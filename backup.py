#!/usr/bin/env python3
"""
Backup inteligent Linux -> exFAT cu sincronizare rsync și detecție mutări.

Structură pe stick:
    /stick/<cale_absoluta_fara_leading_slash>/...    <- backup curent
    /stick/_Istoric/home/<user>/<timestamp>/...      <- istoric per-user

Fiecare user are istoricul lui, curățat independent.
"""

import os
import sys
import time
import shutil
import subprocess
import hashlib
import re
import argparse
import fnmatch
import getpass
from datetime import datetime

# ==========================================
# CONSTANTE
# ==========================================
MARJA_SIGURANTA_MB = 200
ZILE_PASTRARE_ISTORIC = 30

# Toleranță la compararea mtime pentru exFAT (rezoluție 2s, rotunjire variabilă)
MODIFY_WINDOW = 2

EXCLUDERI_FISIERE = [
    "*.tmp", "*~", ".~lock.*", "*.part", "*.crdownload",
    "thumbs.db", ".DS_Store", "desktop.ini",
]
EXCLUDERI_DIRECTOARE = [
    "__pycache__", ".pytest_cache", ".thumbnails",
    ".Trash-*", "$RECYCLE.BIN", "System Volume Information",
]

CARACTERE_INTERZISE = r'[\\:*?\"<>|]'

# Nume rezervate pe Windows/exFAT (case-insensitive, indiferent de extensie)
NUME_REZERVATE = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}

# ==========================================
# CULORI ȘI EMOJI
# ==========================================
CULORI = {
    "rosu":     "\033[91m",
    "verde":    "\033[92m",
    "galben":   "\033[93m",
    "albastru": "\033[94m",
    "magenta":  "\033[95m",
    "cyan":     "\033[96m",
    "alb":      "\033[97m",
    "gri":      "\033[90m",
    "bold":     "\033[1m",
    "reset":    "\033[0m",
}

EMOJI = {
    "folder":     "📁",
    "index":      "🔍",
    "sync":       "🔄",
    "mutare":     "↔️ ",
    "stergere":   "🗑️ ",
    "redenumire": "✏️ ",
    "succes":     "✅",
    "eroare":     "❌",
    "avert":      "⚠️ ",
    "info":       "ℹ️ ",
    "istoric":    "📜",
    "spatiu":     "💾",
    "timp":       "⏱️ ",
    "sumar":      "📊",
    "locatie":    "📍",
}

ANSI_REGEX = re.compile(r'\033\[[0-9;]*m')


def strip_ansi(s):
    """Elimină codurile ANSI pentru calculul lungimii reale."""
    return ANSI_REGEX.sub('', s)


def lungime_vizuala(s):
    """Lungimea reală afișată în terminal (ANSI = 0, emoji wide = 2)."""
    s = strip_ansi(s)
    lungime = 0
    for c in s:
        cp = ord(c)
        if cp >= 0x1F300 or cp == 0xFE0F or cp == 0x20E3:
            lungime += 2
        elif 0x2600 <= cp <= 0x27BF:
            lungime += 2
        else:
            lungime += 1
    return lungime


def colorat(text, culoare):
    """Colorează textul doar dacă output-ul e un terminal."""
    if not sys.stdout.isatty():
        return text
    return f"{CULORI.get(culoare, '')}{text}{CULORI['reset']}"


def banner(titlu, subtitlu=None, latime=54, culoare="albastru"):
    """Banner elegant cu chenar dublu."""
    sus = "╔" + "═" * (latime - 2) + "╗"
    jos = "╚" + "═" * (latime - 2) + "╝"

    def centreaza(text):
        lung = lungime_vizuala(text)
        padding = (latime - 2 - lung) // 2
        rest = latime - 2 - lung - padding
        return "║" + " " * padding + text + " " * rest + "║"

    linii = [sus, centreaza(titlu)]
    if subtitlu:
        linii.append(centreaza(subtitlu))
    linii.append(jos)

    return "\n".join(colorat(l, culoare) for l in linii)


def linie_separator(latime=54, culoare="gri"):
    """Linie de separare între secțiuni."""
    return colorat("━" * latime, culoare)


# ==========================================
# PARSARE ARGUMENTE
# ==========================================
def parse_args():
    parser = argparse.ArgumentParser(
        description="Backup inteligent Linux -> exFAT cu rsync și detecție mutări.",
        epilog=(
            "Exemple:\n"
            "  %(prog)s ~/Desktop ~/Documents /media/dan/stick\n"
            "  %(prog)s ~/Desktop /media/dan/stick --dry-run\n"
            "  %(prog)s ~/Desktop /media/dan/stick --verbose\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        'cai', nargs='*',
        help='Căile sursă urmate de calea destinație (ultimul = destinația)'
    )
    parser.add_argument(
        '-n', '--dry-run', action='store_true',
        help='Simulare fără modificări fizice'
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='Output detaliat rsync (listing complet per fișier)'
    )
    parser.add_argument(
        '--marja-mb', type=int, default=MARJA_SIGURANTA_MB,
        help=f'Marjă de siguranță în MB (default: {MARJA_SIGURANTA_MB})'
    )
    parser.add_argument(
        '--zile-istoric', type=int, default=ZILE_PASTRARE_ISTORIC,
        help=f'Zile de păstrare istoric (default: {ZILE_PASTRARE_ISTORIC})'
    )
    return parser.parse_args()


# ==========================================
# UTILITARE
# ==========================================
def pauza_finala():
    if sys.stdin.isatty():
        try:
            input("Apasă Enter pentru a închide...")
        except EOFError:
            pass


def trimite_notificare(titlu, mesaj, iconita="dialog-information"):
    if not shutil.which("notify-send"):
        return
    try:
        env = os.environ.copy()
        uid = os.getuid()
        if "XDG_RUNTIME_DIR" not in env:
            env["XDG_RUNTIME_DIR"] = f"/run/user/{uid}"
        if "DBUS_SESSION_BUS_ADDRESS" not in env:
            env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{uid}/bus"
        subprocess.run(
            ["notify-send", "-i", iconita, titlu, mesaj],
            env=env, check=False,
        )
    except Exception:
        pass


def e_exclus_fisier(nume):
    return any(fnmatch.fnmatch(nume, p) for p in EXCLUDERI_FISIERE)


def e_exclus_folder(nume):
    return any(fnmatch.fnmatch(nume, p) for p in EXCLUDERI_DIRECTOARE)


def walk_filtrat(radacina):
    """os.walk care respectă EXCLUDERI (consistență cu rsync)."""
    for root, dirs, files in os.walk(radacina):
        dirs[:] = [d for d in dirs if not e_exclus_folder(d)]
        fisiere_ok = [f for f in files if not e_exclus_fisier(f)]
        yield root, dirs, fisiere_ok


def explica_eroare_rsync(cod):
    """Explicații pentru codurile frecvente de eroare rsync."""
    explicatii = {
        1:  "Eroare de sintaxă sau utilizare",
        2:  "Eroare de protocol",
        3:  "Eroare la selectarea fișierelor de intrare",
        4:  "Acțiune nesuportată",
        5:  "Eroare la pornirea clientului",
        6:  "Eroare la încărcarea jurnalului",
        10: "Eroare socket I/O",
        11: "Eroare I/O fișier (spațiu, permisiuni, disc deconectat)",
        12: "Eroare protocol de date",
        13: "Eroare la diagnosticare",
        14: "Eroare la IPC",
        20: "Semnal primit (SIGUSR1/SIGINT)",
        21: "Așteptare pentru pid",
        22: "Eroare la alocarea buffer-ului",
        23: "Fișiere parțial transferate (modificare în timpul copierii)",
        24: "Fișiere sursă dispărute în timpul transferului",
        25: "Limită --max-delete atinsă",
        30: "Timeout de date",
        35: "Timeout de conexiune",
    }
    return explicatii.get(cod, "Cod necunoscut")


# ==========================================
# VALIDARE NUME exFAT / WINDOWS
# ==========================================
def e_nume_invalid_exfat(nume):
    """
    Verifică dacă numele e problematic pentru exFAT/Windows.

    Cazuri:
    - Caractere interzise: \\ : * ? " < > |
    - Nume rezervate: CON, PRN, AUX, NUL, COM1-9, LPT1-9 (indiferent de extensie)
    - Termină cu spațiu sau punct
    - E gol
    """
    if not nume:
        return True

    # Caractere interzise
    if re.search(CARACTERE_INTERZISE, nume):
        return True

    # Termină cu spațiu sau punct
    if nume != nume.rstrip(' .'):
        return True

    # Nume rezervate (verificăm baza fără extensie)
    baza = nume.split('.')[0].upper()
    if baza in NUME_REZERVATE:
        return True

    return False


def curata_nume_exfat(nume):
    """
    Curăță numele pentru compatibilitate exFAT/Windows.
    Returnează numele curățat.
    """
    # 1. Înlocuiește caracterele interzise
    nume_curat = re.sub(CARACTERE_INTERZISE, '_', nume)

    # 2. Elimină spații și puncte de la final
    nume_curat = nume_curat.rstrip(' .')

    # 3. Verifică nume rezervate (indiferent de extensie)
    baza, ext = os.path.splitext(nume_curat)
    if baza.upper() in NUME_REZERVATE:
        nume_curat = f"_{baza}{ext}"

    # 4. Dacă e gol, pune nume default
    if not nume_curat:
        nume_curat = "_fisier_fara_nume"

    return nume_curat


def generat_cale_unica_curata(cale_veche):
    """
    Generează o cale cu nume curățat pentru exFAT.
    Dacă numele era deja valid, returnează calea originală.
    Dacă după curățare apare conflict, adaugă _1, _2, ...
    """
    cale_dir, nume_vechi = os.path.split(cale_veche)

    if not e_nume_invalid_exfat(nume_vechi):
        return cale_veche

    nume_curat = curata_nume_exfat(nume_vechi)

    if nume_curat == nume_vechi:
        return cale_veche

    cale_noua = os.path.join(cale_dir, nume_curat)

    # Dacă există deja un fișier cu acest nume, adaugă _1, _2, ...
    if os.path.exists(cale_noua) and cale_noua != cale_veche:
        nume_baza, extensie = os.path.splitext(nume_curat)
        contor = 1
        while True:
            nume_propus = f"{nume_baza}_{contor}{extensie}"
            cale_propusa = os.path.join(cale_dir, nume_propus)
            if not os.path.exists(cale_propusa):
                cale_noua = cale_propusa
                break
            contor += 1

    return cale_noua


# ==========================================
# HASH RAPID
# ==========================================
def calculeaza_hash_rapid(cale_fisier):
    try:
        marime = os.path.getsize(cale_fisier)
        if marime == 0:
            return ("empty_file", 0)

        hasher = hashlib.md5()
        hasher.update(str(marime).encode('utf-8'))

        with open(cale_fisier, 'rb') as f:
            hasher.update(f.read(65536))
            if marime > 131072:
                f.seek(-65536, os.SEEK_END)
                hasher.update(f.read(65536))

        return (hasher.hexdigest(), marime)
    except OSError:
        return None


# ==========================================
# VERIFICĂRI PRELIMINARE
# ==========================================
def verifica_mediu():
    if os.geteuid() == 0:
        print(colorat(f"{EMOJI['eroare']} EROARE: Nu rula scriptul ca root/sudo! Rulează ca user normal.", "rosu"))
        sys.exit(1)


def verifica_destinatie(destinatie, is_dry_run):
    if not os.path.exists(destinatie):
        msg = f"HDD-ul extern nu este conectat la: {destinatie}"
        print(banner("BACKUP EȘUAT", msg, latime=70, culoare="rosu"))
        trimite_notificare("Backup Eșuat", msg, iconita="dialog-error")
        pauza_finala()
        sys.exit(1)

    if not is_dry_run:
        cale_test = os.path.join(destinatie, ".test_scriere.tmp")
        try:
            with open(cale_test, "w") as f:
                f.write("test")
            os.remove(cale_test)
        except OSError:
            msg = "HDD-ul extern este montat Read-Only!"
            print(banner("BACKUP EȘUAT", msg, latime=70, culoare="rosu"))
            print(colorat("Recomandare: deconectează și reconectează HDD-ul sau verifică-l cu fsck.exfat.", "galben"))
            trimite_notificare("Backup Eșuat", msg, iconita="dialog-error")
            pauza_finala()
            sys.exit(1)


def verifica_surse_si_destinatie(foldere_sursa, destinatia_baza):
    """
    Verificări de suprapunere între surse și destinație.

    1. Sursele între ele nu trebuie să se suprapună
    2. Nicio sursă nu trebuie să fie în interiorul destinației
    3. Destinația nu trebuie să fie în interiorul vreunei surse
    """
    # 1. Sursele între ele
    for i, s1 in enumerate(foldere_sursa):
        for s2 in foldere_sursa[i + 1:]:
            try:
                if (os.path.commonpath([s1, s2]) == s1
                        or os.path.commonpath([s1, s2]) == s2):
                    print(banner("EROARE SURSE SUPRAPUSE", None, latime=70, culoare="rosu"))
                    print(colorat(f"  - {s1}", "rosu"))
                    print(colorat(f"  - {s2}", "rosu"))
                    pauza_finala()
                    sys.exit(1)
            except ValueError:
                pass

    # 2 și 3. Sursă <-> Destinație (verificare simetrică)
    for sursa in foldere_sursa:
        try:
            comun = os.path.commonpath([sursa, destinatia_baza])
            if comun == destinatia_baza or comun == sursa:
                print(banner("EROARE SUPRAPUNERE", None, latime=70, culoare="rosu"))
                if comun == destinatia_baza:
                    print(colorat(f"  Sursa este în interiorul destinației:", "rosu"))
                    print(colorat(f"    sursă:      {sursa}", "rosu"))
                    print(colorat(f"    destinație: {destinatia_baza}", "rosu"))
                else:
                    print(colorat(f"  Destinația este în interiorul sursei:", "rosu"))
                    print(colorat(f"    sursă:      {sursa}", "rosu"))
                    print(colorat(f"    destinație: {destinatia_baza}", "rosu"))
                    print()
                    print(colorat("  Acest lucru ar cauza copiere recursivă (backup-ul se", "galben"))
                    print(colorat("  copiază pe el însuși) și ar umple discul!", "galben"))
                pauza_finala()
                sys.exit(1)
        except ValueError:
            pass


# ==========================================
# PLANIFICARE (Pas I - read-only)
# ==========================================
def autocurata_nume(sursa_abs, is_dry_run, log_redenumiri):
    modificari = 0

    for root, dirs, files in os.walk(sursa_abs, topdown=False):
        for f in files:
            if e_nume_invalid_exfat(f):
                cale_veche = os.path.join(root, f)
                cale_noua = generat_cale_unica_curata(cale_veche)
                if cale_noua == cale_veche:
                    continue
                if not is_dry_run:
                    try:
                        os.rename(cale_veche, cale_noua)
                    except OSError as e:
                        print(colorat(f"    {EMOJI['eroare']} Eroare redenumire {cale_veche}: {e}", "rosu"))
                        continue
                mesaj = f"[Fișier] {cale_veche} --> {os.path.basename(cale_noua)}"
                prefix = colorat("[SIMULARE] ", "galben") if is_dry_run else ""
                print(f"    {prefix}{EMOJI['redenumire']} {mesaj}")
                log_redenumiri.append(mesaj)
                modificari += 1

        for d in dirs:
            if e_nume_invalid_exfat(d):
                cale_veche = os.path.join(root, d)
                cale_noua = generat_cale_unica_curata(cale_veche)
                if cale_noua == cale_veche:
                    continue
                if not is_dry_run:
                    try:
                        os.rename(cale_veche, cale_noua)
                    except OSError as e:
                        print(colorat(f"    {EMOJI['eroare']} Eroare redenumire {cale_veche}: {e}", "rosu"))
                        continue
                mesaj = f"[Folder] {cale_veche} --> {os.path.basename(cale_noua)}"
                prefix = colorat("[SIMULARE] ", "galben") if is_dry_run else ""
                print(f"    {prefix}{EMOJI['redenumire']} {mesaj}")
                log_redenumiri.append(mesaj)
                modificari += 1

    return modificari


def indexeaza_sursa(sursa_abs):
    fisiere_exacte = set()
    dupa_hash = {}
    contor = 0

    for root, _, files in walk_filtrat(sursa_abs):
        for f in files:
            cale_abs = os.path.join(root, f)
            cale_rel = os.path.relpath(cale_abs, sursa_abs)
            fisiere_exacte.add(cale_rel)
            contor += 1

            if contor % 1000 == 0:
                print(f"\r    {EMOJI['index']} Indexare... {contor} fișiere", end="", flush=True)

            amprenta = calculeaza_hash_rapid(cale_abs)
            if amprenta:
                dupa_hash.setdefault(amprenta, []).append(cale_rel)

    if contor >= 1000:
        print()

    return fisiere_exacte, dupa_hash, contor


def calculeaza_spatiu_necesar(sursa_abs, destinatia_folder):
    """
    Calculează spațiul necesar pentru sincronizare.

    Replică EXACT logica rsync de comparație:
    - Default rsync: mtime + size cu --modify-window=MODIFY_WINDOW
    - Pentru fișiere modificate: adaugă mărimea versiunii noi + mărimea
      versiunii vechi (care rămâne în _MODIF via --backup-dir)
    - Pentru fișiere noi: adaugă doar mărimea lor
    """
    total = 0

    for root, _, files in walk_filtrat(sursa_abs):
        for f in files:
            cale_abs = os.path.join(root, f)
            cale_rel = os.path.relpath(cale_abs, sursa_abs)
            cale_hdd = os.path.join(destinatia_folder, cale_rel)

            try:
                st_sursa = os.stat(cale_abs)
                marime_sursa = st_sursa.st_size

                st_hdd = None
                if os.path.exists(cale_hdd):
                    try:
                        st_hdd = os.stat(cale_hdd)
                    except OSError:
                        st_hdd = None

                if st_hdd is None:
                    # Fișier nou — va fi copiat
                    total += marime_sursa
                elif (st_hdd.st_size != marime_sursa
                      or abs(st_hdd.st_mtime - st_sursa.st_mtime) > MODIFY_WINDOW):
                    # Fișier modificat — versiunea nouă + versiunea veche în _MODIF
                    total += marime_sursa + st_hdd.st_size
                # else: identic, nu consumă spațiu

            except OSError:
                pass

    return total


# ==========================================
# EXECUȚIE (Pas III - modifică HDD)
# ==========================================
def detecteaza_mutari_si_stergeri(
    destinatia_folder, sursa_abs,
    fisiere_sursa_exacte, fisiere_sursa_dupa_hash,
    dir_sterse, is_dry_run, contoare,
):
    if not os.path.exists(destinatia_folder):
        return

    for root, _, files in walk_filtrat(destinatia_folder):
        for f in files:
            cale_hdd_abs = os.path.join(root, f)
            cale_rel = os.path.relpath(cale_hdd_abs, destinatia_folder)

            if cale_rel in fisiere_sursa_exacte:
                continue

            amprenta_hdd = calculeaza_hash_rapid(cale_hdd_abs)
            candidati = fisiere_sursa_dupa_hash.get(amprenta_hdd, []) if amprenta_hdd else []

            if candidati:
                # Fișier mutat în sursă
                cale_noua_rel = candidati.pop(0)
                cale_noua_hdd_abs = os.path.join(destinatia_folder, cale_noua_rel)

                if is_dry_run:
                    print(f"    {colorat('[SIMULARE]', 'galben')} {EMOJI['mutare']} {cale_rel} → {cale_noua_rel}")
                    contoare["mutate"] += 1
                    fisiere_sursa_exacte.add(cale_noua_rel)
                else:
                    try:
                        os.makedirs(os.path.dirname(cale_noua_hdd_abs), exist_ok=True)
                        shutil.move(cale_hdd_abs, cale_noua_hdd_abs)
                        cale_sursa_laptop = os.path.join(sursa_abs, cale_noua_rel)
                        try:
                            st = os.stat(cale_sursa_laptop)
                            os.utime(cale_noua_hdd_abs, (st.st_atime, st.st_mtime))
                        except OSError:
                            pass
                        print(f"    {colorat(EMOJI['mutare'], 'cyan')} {cale_rel} → {cale_noua_rel}")
                        contoare["mutate"] += 1
                        fisiere_sursa_exacte.add(cale_noua_rel)
                    except OSError as e:
                        print(colorat(f"    {EMOJI['eroare']} Eroare mutare {cale_rel}: {e}", "rosu"))
            else:
                # Fișier șters din sursă
                dest_sterse_abs = os.path.join(dir_sterse, cale_rel)

                if is_dry_run:
                    print(f"    {colorat('[SIMULARE]', 'galben')} {EMOJI['stergere']} {cale_rel} → _STERS/")
                    contoare["sterse"] += 1
                else:
                    try:
                        os.makedirs(os.path.dirname(dest_sterse_abs), exist_ok=True)
                        shutil.move(cale_hdd_abs, dest_sterse_abs)
                        print(f"    {colorat(EMOJI['stergere'], 'magenta')} {cale_rel} → _STERS/")
                        contoare["sterse"] += 1
                    except OSError as e:
                        print(colorat(f"    {EMOJI['eroare']} Eroare ștergere {cale_rel}: {e}", "rosu"))


def ruleaza_rsync(sursa_abs, destinatia_folder, dir_modificate, is_dry_run, verbose=False):
    """
    Rulează rsync și returnează (returncode, statistici).

    Comparație: default rsync (mtime + size) cu --modify-window=2 pentru
    toleranță la precizia de 2 secunde și rotunjirea variabilă a exFAT.
    Fără --size-only (care rata modificările cu aceeași mărime — bug grav).
    """
    if not is_dry_run:
        try:
            os.makedirs(destinatia_folder, exist_ok=True)
        except OSError as e:
            print(colorat(f"    {EMOJI['eroare']} Nu pot crea destinația {destinatia_folder}: {e}", "rosu"))
            return 1, {}

    cmd = ["rsync", "-rt", f"--modify-window={MODIFY_WINDOW}"]

    if verbose:
        cmd.extend(["-v", "--info=progress2,stats2,name"])
    else:
        cmd.extend(["--info=name,stats2"])

    cmd.extend([
        "--backup", f"--backup-dir={dir_modificate}",
        f"{sursa_abs}/", f"{destinatia_folder}/",
    ])
    for p in EXCLUDERI_FISIERE + EXCLUDERI_DIRECTOARE:
        cmd.extend(["--exclude", p])

    if is_dry_run:
        cmd.append("--dry-run")

    rezultat = subprocess.run(cmd, capture_output=True, text=True)

    if rezultat.stdout:
        print(rezultat.stdout, end="")
    if rezultat.stderr:
        print(rezultat.stderr, end="", file=sys.stderr)

    statistici = {}
    for linie in rezultat.stdout.splitlines():
        m = re.match(r"Number of created files:\s*(\d+)", linie)
        if m:
            statistici["create"] = int(m.group(1))
        m = re.match(r"Number of regular files transferred:\s*(\d+)", linie)
        if m:
            statistici["transferate"] = int(m.group(1))

    return rezultat.returncode, statistici


# ==========================================
# CURĂȚARE
# ==========================================
def curata_istoric_user(dir_istoric_user, zile):
    if not os.path.isdir(dir_istoric_user):
        return 0

    prag = time.time() - zile * 86400
    sterse = 0

    for entry in os.listdir(dir_istoric_user):
        cale = os.path.join(dir_istoric_user, entry)
        if os.path.isdir(cale):
            try:
                if os.path.getmtime(cale) < prag:
                    shutil.rmtree(cale, ignore_errors=True)
                    sterse += 1
            except OSError:
                pass

    return sterse


def curata_foldere_goale(radacina):
    """
    Șterge recursive folderele goale.
    Repetă bottom-up până nu mai șterge nimic (cascadă).
    """
    if not os.path.isdir(radacina):
        return

    while True:
        sters_ceva = False
        for root, dirs, files in os.walk(radacina, topdown=False):
            for d in dirs:
                cale = os.path.join(root, d)
                try:
                    if not os.listdir(cale):
                        os.rmdir(cale)
                        sters_ceva = True
                except OSError:
                    pass
        if not sters_ceva:
            break


def curata_foldere_goale_destinatie(destinatia_folder, dir_sterse, dir_modificate):
    """
    Curăță folderele goale rămase după mutări/ștergeri/rsync.
    Se aplică pe toate cele 3 locații relevante.
    """
    for cale in (destinatia_folder, dir_sterse, dir_modificate):
        if cale and os.path.isdir(cale):
            curata_foldere_goale(cale)


# ==========================================
# SUMAR
# ==========================================
def afiseaza_sumar(latime, culoare_final, plan, contoare, istoric_sters,
                   durata_str, spatiu_necesar_mb, spatiu_liber_mb, erori_rsync):
    """Afișează sumarul final aliniat corect."""

    def linie(eticheta, valoare, valoare_colorata=None):
        if valoare_colorata is None:
            valoare_colorata = valoare

        text_simplu = f"  {eticheta:<22} {valoare}"
        lungime_reala = lungime_vizuala(text_simplu)
        padding = latime - 2 - lungime_reala
        if padding < 0:
            padding = 0

        text_afisat = f"  {eticheta:<22} {valoare_colorata}"
        return (
            colorat("║", culoare_final)
            + text_afisat
            + " " * padding
            + colorat("║", culoare_final)
        )

    def linie_titlu(text):
        lung = lungime_vizuala(text)
        padding = (latime - 2 - lung) // 2
        rest = latime - 2 - lung - padding
        return colorat("║", culoare_final) + " " * padding + text + " " * rest + colorat("║", culoare_final)

    print(banner("BACKUP FINALIZAT CU ERORI" if erori_rsync else "BACKUP FINALIZAT",
                 None, latime=latime, culoare=culoare_final))

    print(colorat("╔" + "═" * (latime - 2) + "╗", culoare_final))
    print(linie_titlu(f"{EMOJI['sumar']}  SUMAR"))
    print(colorat("╠" + "═" * (latime - 2) + "╣", culoare_final))

    print(linie("Surse procesate:", f"{len(plan)}"))
    print(linie("Fișiere noi:", str(contoare["noi"]), colorat(str(contoare["noi"]), "verde")))
    print(linie("Fișiere modificate:", str(contoare["modificate"]), colorat(str(contoare["modificate"]), "galben")))
    print(linie("Fișiere mutate:", str(contoare["mutate"]), colorat(str(contoare["mutate"]), "cyan")))
    print(linie("Fișiere șterse:", str(contoare["sterse"]), colorat(str(contoare["sterse"]), "magenta")))
    print(linie("Redenumiri:", str(contoare["redenumiri"])))

    if istoric_sters:
        print(linie("Sesiuni istoric șterse:", str(istoric_sters)))

    print(colorat("╠" + "═" * (latime - 2) + "╣", culoare_final))
    print(linie("Durată:", durata_str))
    print(linie("Date transferate:", f"{spatiu_necesar_mb:.2f} MB"))
    print(linie("Spațiu rămas:", f"{spatiu_liber_mb:.1f} MB"))

    if erori_rsync:
        print(colorat("╠" + "═" * (latime - 2) + "╣", culoare_final))
        print(linie("Erori rsync:", str(len(erori_rsync)), colorat(str(len(erori_rsync)), "rosu")))

    print(colorat("╚" + "═" * (latime - 2) + "╝", culoare_final))


def afiseaza_locatii(plan, dir_sesiune_curenta, erori_rsync, is_dry_run):
    """
    Afișează locațiile reale ale backup-ului (cale completă pentru fiecare sursă).
    """
    if is_dry_run:
        return

    print()

    if len(plan) == 1:
        # O singură sursă — afișăm direct
        # plan conține tuplu cu 6 elemente acum: (sursa, destinatie, dir_modif, dir_sterse, fis, hash)
        _, destinatie_folder = plan[0][0], plan[0][1]
        print(f"{EMOJI['locatie']} {colorat('Backup:', 'bold')} {destinatie_folder}/")
    else:
        # Mai multe surse — le listăm pe fiecare
        print(f"{EMOJI['locatie']} {colorat('Backup:', 'bold')}")
        for entry in plan:
            destinatie_folder = entry[1]
            print(f"   {destinatie_folder}/")

    if not erori_rsync:
        print(f"{EMOJI['locatie']} {colorat('Istoric:', 'bold')} {dir_sesiune_curenta}/")


# ==========================================
# MAIN
# ==========================================
def main():
    start_time = time.time()
    args = parse_args()

    if len(args.cai) < 2:
        print(colorat(f"{EMOJI['eroare']} EROARE: Specifică cel puțin o sursă și o destinație!\n", "rosu"))
        print(colorat("Exemple:", "cyan"))
        print("  ./backup.py ~/Desktop ~/Documents /media/dan/stick")
        print("  ./backup.py ~/Desktop /media/dan/stick --dry-run")
        print("  ./backup.py ~/Desktop /media/dan/stick --verbose\n")
        pauza_finala()
        sys.exit(1)

    verifica_mediu()

    is_dry_run = args.dry_run
    verbose = args.verbose
    user_curent = getpass.getuser()

    destinatia_baza = os.path.abspath(os.path.expanduser(args.cai[-1]))
    foldere_sursa = [
        os.path.abspath(os.path.expanduser(p)) for p in args.cai[:-1]
    ]

    # Verificare completă surse <-> destinație (simetrică)
    verifica_surse_si_destinatie(foldere_sursa, destinatia_baza)

    verifica_destinatie(destinatia_baza, is_dry_run)

    # Structura destinației
    dir_istoric_baza = os.path.join(destinatia_baza, "_Istoric")
    dir_istoric_user = os.path.join(dir_istoric_baza, "home", user_curent)

    acum = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dir_sesiune_curenta = os.path.join(dir_istoric_user, acum)
    dir_sterse_sesiune = os.path.join(dir_sesiune_curenta, "_STERS")
    dir_modificate_sesiune = os.path.join(dir_sesiune_curenta, "_MODIF")
    cale_log_redenumiri = os.path.join(dir_sesiune_curenta, "redenumiri.log")

    _, _, free = shutil.disk_usage(destinatia_baza)
    spatiu_liber_gb = free / (1024 ** 3)

    titlu = "BACKUP SIMULARE" if is_dry_run else "BACKUP INTELIGENT"
    subtitlu = f"Spațiu liber: {spatiu_liber_gb:.1f} GB"
    print(banner(titlu, subtitlu, culoare="galben" if is_dry_run else "cyan"))

    if is_dry_run:
        trimite_notificare("Backup SIMULARE", "A început simularea backup-ului.")
    else:
        trimite_notificare(
            "Backup Inițializat",
            f"Sincronizare pe HDD ({spatiu_liber_gb:.1f} GB liberi).",
        )

    # ==========================================
    # PASUL I: Planificare (read-only pe HDD)
    # ==========================================
    log_redenumiri = []
    spatiu_total_necesar = 0
    plan = []
    contoare = {"noi": 0, "modificate": 0, "mutate": 0, "sterse": 0, "redenumiri": 0}
    total_surse = len([s for s in foldere_sursa if os.path.exists(s)])
    idx_sursa = 0

    for sursa_abs in foldere_sursa:
        if not os.path.exists(sursa_abs):
            print()
            print(colorat(f"{EMOJI['avert']} Folderul sursă nu există: {sursa_abs} (se omite)", "galben"))
            continue

        idx_sursa += 1
        cale_relativa = sursa_abs.lstrip(os.sep)
        destinatia_folder = os.path.join(destinatia_baza, cale_relativa)

        dir_sterse = os.path.join(dir_sterse_sesiune, cale_relativa)
        dir_modificate = os.path.join(dir_modificate_sesiune, cale_relativa)

        print()
        print(linie_separator())
        print(f"{EMOJI['folder']} {colorat(f'[{idx_sursa}/{total_surse}]', 'bold')} {colorat(sursa_abs, 'cyan')}")
        print(linie_separator())

        print(f"  {colorat('[1/3]', 'gri')} {EMOJI['redenumire']} Autocurățare nume...")
        modificari = autocurata_nume(sursa_abs, is_dry_run, log_redenumiri)
        contoare["redenumiri"] += modificari
        if modificari == 0:
            print(f"         {colorat('Toate numele sunt compatibile exFAT.', 'gri')}")

        print(f"  {colorat('[2/3]', 'gri')} {EMOJI['index']} Indexare fișiere...")
        fisiere_exacte, dupa_hash, nr_fisiere = indexeaza_sursa(sursa_abs)
        print(f"         {colorat(f'{nr_fisiere} fișiere indexate', 'gri')}")

        spatiu_sursa = calculeaza_spatiu_necesar(sursa_abs, destinatia_folder)
        spatiu_total_necesar += spatiu_sursa
        print(f"  {colorat('[3/3]', 'gri')} {EMOJI['spatiu']} Spațiu necesar: "
              f"{colorat(f'{spatiu_sursa / (1024**2):.2f} MB', 'cyan')}")

        # Plan: fără modificări pe HDD încă
        plan.append((
            sursa_abs,
            destinatia_folder,
            dir_modificate,
            dir_sterse,
            fisiere_exacte,
            dupa_hash,
        ))

    # ==========================================
    # PASUL II: Verificare spațiu agregat
    # (FĂRĂ modificări pe HDD până aici)
    # ==========================================
    _, _, free = shutil.disk_usage(destinatia_baza)
    marja_bytes = args.marja_mb * 1024 * 1024
    necesar_total = spatiu_total_necesar + marja_bytes

    spatiu_necesar_mb = spatiu_total_necesar / (1024 ** 2)
    spatiu_liber_mb = free / (1024 ** 2)

    print()
    print(linie_separator())
    print(f"{EMOJI['spatiu']} {colorat('VERIFICARE SPAȚIU', 'bold')}")
    print(linie_separator())
    print(f"  Date noi/modificate: {colorat(f'{spatiu_necesar_mb:.2f} MB', 'cyan')}")
    print(f"  Marjă de siguranță:  {colorat(f'{args.marja_mb} MB', 'gri')}")
    print(f"  Spațiu liber:        {colorat(f'{spatiu_liber_mb:.2f} MB', 'verde')}")

    if free < necesar_total:
        msg = (
            f"Spațiu insuficient! Necesar: {spatiu_necesar_mb:.1f} MB + {args.marja_mb} MB marjă, "
            f"liber: {spatiu_liber_mb:.1f} MB"
        )
        print()
        print(banner("BACKUP EȘUAT", msg, latime=70, culoare="rosu"))
        print(colorat("Sincronizarea a fost OPRITĂ pentru a preveni umplerea discului.", "galben"))
        print(colorat("Nicio modificare nu a fost aplicată pe HDD.", "galben"))
        trimite_notificare("Backup Eșuat", msg, iconita="dialog-error")
        pauza_finala()
        sys.exit(1)

    # ==========================================
    # PASUL III: Execuție (modifică HDD-ul)
    # ==========================================
    print()
    print(linie_separator())
    print(f"{EMOJI['sync']} {colorat('EXECUȚIE BACKUP', 'bold')}")
    print(linie_separator())

    erori_rsync = []
    total_create = 0
    total_transferate = 0

    for idx_exec, entry in enumerate(plan, 1):
        sursa_abs, destinatia_folder, dir_modificate, dir_sterse, fisiere_exacte, dupa_hash = entry

        print()
        print(f"{EMOJI['folder']} {colorat(f'[{idx_exec}/{len(plan)}]', 'bold')} {colorat(sursa_abs, 'cyan')}")

        # 3a. Detecție mutări/ștergeri (modifică HDD-ul)
        print(f"    {EMOJI['sync']} Detecție mutări/ștergeri...")
        mutari_inainte = contoare["mutate"]
        stergeri_inainte = contoare["sterse"]
        detecteaza_mutari_si_stergeri(
            destinatia_folder, sursa_abs,
            fisiere_exacte, dupa_hash,
            dir_sterse, is_dry_run, contoare,
        )
        mutari_sursa = contoare["mutate"] - mutari_inainte
        stergeri_sursa = contoare["sterse"] - stergeri_inainte
        if mutari_sursa == 0 and stergeri_sursa == 0:
            print(f"       {colorat('Nicio mutare sau ștergere.', 'gri')}")
        else:
            print(f"       {colorat(f'{mutari_sursa} mutate, {stergeri_sursa} șterse', 'gri')}")

        # 3b. rsync
        print(f"    {EMOJI['sync']} Sincronizare rsync...")
        cod, statistici = ruleaza_rsync(
            sursa_abs, destinatia_folder, dir_modificate, is_dry_run, verbose
        )

        total_create += statistici.get("create", 0)
        total_transferate += statistici.get("transferate", 0)

        if cod != 0:
            if cod in (23, 24):
                print(colorat(f"       {EMOJI['avert']} rsync a returnat {cod} ({explica_eroare_rsync(cod)})", "galben"))
            else:
                erori_rsync.append((sursa_abs, cod))
                print(colorat(f"       {EMOJI['eroare']} rsync a returnat codul {cod}: {explica_eroare_rsync(cod)}", "rosu"))

        # 3c. Curăță folderele goale
        if not is_dry_run:
            curata_foldere_goale_destinatie(
                destinatia_folder, dir_sterse, dir_modificate
            )

    contoare["noi"] = total_create
    contoare["modificate"] = max(0, total_transferate - total_create)

    # ==========================================
    # Salvare log redenumiri
    # ==========================================
    if log_redenumiri and not is_dry_run:
        os.makedirs(dir_sesiune_curenta, exist_ok=True)
        with open(cale_log_redenumiri, "w", encoding="utf-8") as f:
            f.write(f"Jurnal redenumiri din {acum}\n")
            f.write(f"User: {user_curent}\n")
            f.write("=" * 50 + "\n\n")
            f.write("\n".join(log_redenumiri))

    # ==========================================
    # Curățare istoric
    # ==========================================
    istoric_sters = 0
    if not is_dry_run:
        curata_foldere_goale(dir_sesiune_curenta)

        print()
        print(f"  {EMOJI['istoric']} Curățare istoric > {args.zile_istoric} zile pentru {user_curent}...")
        istoric_sters = curata_istoric_user(dir_istoric_user, args.zile_istoric)
        if istoric_sters:
            print(f"         {colorat(f'{istoric_sters} sesiuni vechi șterse', 'gri')}")

    # ==========================================
    # Calcul durată
    # ==========================================
    durata = time.time() - start_time
    if durata < 60:
        durata_str = f"{durata:.1f} secunde"
    else:
        minute = int(durata // 60)
        secunde = int(durata % 60)
        durata_str = f"{minute}m {secunde}s"

    # ==========================================
    # Notificare finală + SUMAR
    # ==========================================
    if erori_rsync:
        msg = f"Backup cu erori la: {', '.join(s for s, _ in erori_rsync)}"
        trimite_notificare("Backup cu Erori", msg, iconita="dialog-warning")
        culoare_final = "rosu"
    elif is_dry_run:
        trimite_notificare("Simulare Finalizată", "Simularea s-a încheiat.")
        culoare_final = "galben"
    else:
        trimite_notificare("Backup Finalizat", "Sincronizarea s-a încheiat cu succes!")
        culoare_final = "verde"

    latime_sumar = 54
    print()
    afiseaza_sumar(
        latime_sumar, culoare_final, plan, contoare, istoric_sters,
        durata_str, spatiu_necesar_mb, spatiu_liber_mb, erori_rsync,
    )

    # Locații reale (cale completă pentru fiecare sursă)
    afiseaza_locatii(plan, dir_sesiune_curenta, erori_rsync, is_dry_run)

    print()
    pauza_finala()

    sys.exit(1 if erori_rsync else 0)


if __name__ == "__main__":
    main()
