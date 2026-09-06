#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
import hashlib
import re
import argparse
from datetime import datetime

# ==========================================
# PARSARE PARAMETRI DIN LINIA DE COMANDĂ
# ==========================================
parser = argparse.ArgumentParser(
    description="Backup inteligent Linux -> exFAT cu sincronizare rsync și detecție mutări.",
    usage="%(prog)s sursa1 [sursa2 ...] destinatie [--dry-run]"
)

parser.add_argument(
    'cai',
    nargs='*',
    help='Căile sursă urmate de calea destinație (ultimul argument reprezintă destinația)'
)

parser.add_argument(
    '-n', '--dry-run',
    action='store_true',
    help='Rulează în mod simulare fără a efectua modificări fizice'
)

args = parser.parse_args()

# Verificare existență parametri minimi
if len(args.cai) < 2:
    print("❌ EROARE: Trebuie să specifici cel puțin o cale sursă și o cale destinație!\n")
    print("Exemple de utilizare:")
    print("  ./backup.py ~/Desktop ~/Documents /media/dan/stick")
    print("  ./backup.py ~/Downloads /media/dan/stick --dry-run\n")
    input("Apasă Enter pentru a închide...")
    sys.exit(1)

# Extragere dinamică surse și destinație
DESTINATIA_BAZA = os.path.abspath(os.path.expanduser(args.cai[-1]))
FOLDERE_SURSA = [os.path.abspath(os.path.expanduser(p)) for p in args.cai[:-1]]

# --- VERIFICARE MOD SIMULARE (DRY-RUN) ---
IS_DRY_RUN = args.dry_run or "--dry-run" in sys.argv or "-n" in sys.argv

# --- CONFIGURARE HDD EXTERN ---
DIR_ISTORIC_BAZA = os.path.join(DESTINATIA_BAZA, "_Istoric_Modificari")
MARJA_SIGURANTA_MB = 200  # Marjă minimă în MB pentru stabilitate exFAT

# --- FILTRARE FIȘIERE TEMPORARE ȘI JUNK ---
EXCLUDERI = [
    "*.tmp",
    "*~",
    ".~lock.*",          
    ".Trash-*",          
    "__pycache__",        
    ".pytest_cache",
    ".thumbnails",        
    "thumbs.db",          
    ".DS_Store",          
    "*.part",            
    "*.crdownload"        
]

CARACTERE_INTERZISE = r'[\\:*?\"<>|]'

# --- FUNCȚIE NOTIFICARE ---
def trimite_notificare(titlu, mesaj, iconita="dialog-information"):
    """Trimite o notificare nativă pe desktop-ul Linux."""
    try:
        env = os.environ.copy()
        uid = os.getuid()
        
        if "XDG_RUNTIME_DIR" not in env:
            env["XDG_RUNTIME_DIR"] = f"/run/user/{uid}"
        if "DBUS_SESSION_BUS_ADDRESS" not in env:
            env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{uid}/bus"

        subprocess.run(["notify-send", "-i", iconita, titlu, mesaj], env=env, check=False)
    except Exception:
        pass

def generat_cale_unica_curata(cale_veche):
    cale_dir, nume_vechi = os.path.split(cale_veche)
    nume_curat = re.sub(CARACTERE_INTERZISE, '_', nume_vechi).strip('.')
    
    if nume_curat == nume_vechi:
        return cale_veche
        
    cale_noua = os.path.join(cale_dir, nume_curat)
    
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

# 1. VERIFICARE CONEXIUNE HDD
if not os.path.exists(DESTINATIA_BAZA):
    msg = f"EROARE: HDD-ul extern nu este conectat la calea: {DESTINATIA_BAZA}"
    print("==========================================")
    print(msg)
    print("==========================================")
    trimite_notificare("Backup Eșuat", msg, iconita="dialog-error")
    input("Apasă Enter pentru a închide...")
    sys.exit(1)

# 2. VERIFICARE DACĂ DISCUL ESTE MONTAT ÎN MOD READ-ONLY
if not IS_DRY_RUN:
    cale_test_scriere = os.path.join(DESTINATIA_BAZA, ".test_scriere.tmp")
    try:
        with open(cale_test_scriere, "w") as f:
            f.write("test")
        os.remove(cale_test_scriere)
    except OSError:
        msg = "EROARE: HDD-ul extern este montat în mod Read-Only (Doar citire)!"
        print("==========================================")
        print(f"{msg}")
        print("Recomandare: Deconectează și reconectează HDD-ul sau verifică-l cu fsck.exfat.")
        print("==========================================")
        trimite_notificare("Backup Eșuat", msg, iconita="dialog-error")
        input("Apasă Enter pentru a închide...")
        sys.exit(1)

# Preluare inițială spațiu liber
total, used, free = shutil.disk_usage(DESTINATIA_BAZA)
spatiu_liber_gb = free / (1024 ** 3)

acum = datetime.now().strftime("%Y-%m-%d_%H-%M")
dir_sesiune_curenta = os.path.join(DIR_ISTORIC_BAZA, acum)
dir_sterse_sesiune = os.path.join(dir_sesiune_curenta, "_Fisiere_STERSE")
dir_modificate_sesiune = os.path.join(dir_sesiune_curenta, "_Fisiere_MODIFICATE")
cale_log_redenumiri = os.path.join(dir_sesiune_curenta, "redenumiri.log")

if IS_DRY_RUN:
    trimite_notificare("Backup SIMULARE (Dry-Run)", "A început simularea procesului de backup.")
else:
    trimite_notificare("Backup Inițializat", f"A început sincronizarea pe HDD ({spatiu_liber_gb:.1f} GB liberi).")

print("==========================================")
if IS_DRY_RUN:
    print(f"    [MOD SIMULARE - DRY RUN] Testare backup (Spațiu liber: {spatiu_liber_gb:.1f} GB)...")
else:
    print(f"    Incepe backup-ul inteligent (Spațiu liber: {spatiu_liber_gb:.1f} GB)...")
print("==========================================")

intrari_log_redenumiri = []
spatiu_total_necesar_bytes = 0
plan_sincronizare = []

# PASUL I: Indexare, calcul spațiu și pregătire mutări/ștergeri pe HDD
for sursa_abs in FOLDERE_SURSA:
    if not os.path.exists(sursa_abs):
        print(f"\n[Avertisment] Folderul sursă nu există: {sursa_abs} (se omite)")
        continue

    nume_folder = os.path.basename(sursa_abs.rstrip('/'))
    destinatia_folder = os.path.join(DESTINATIA_BAZA, nume_folder)
    dir_sterse = os.path.join(dir_sterse_sesiune, nume_folder)
    dir_modificate = os.path.join(dir_modificate_sesiune, nume_folder)

    print(f"\n---> Procesare folder: {nume_folder} <---")

    # 0. Autocurățare nume
    print(" -> Autocurățare nume incompatibile pe laptop...")
    modificari_nume = 0
    for root, dirs, files in os.walk(sursa_abs, topdown=False):
        for f in files:
            if re.search(CARACTERE_INTERZISE, f):
                cale_veche = os.path.join(root, f)
                cale_noua = generat_cale_unica_curata(cale_veche)
                if not IS_DRY_RUN:
                    os.rename(cale_veche, cale_noua)
                mesaj = f"[Fișier]  {cale_veche}  -->  {os.path.basename(cale_noua)}"
                print(f"    {'[SIMULARE] ' if IS_DRY_RUN else ''}{mesaj}")
                intrari_log_redenumiri.append(mesaj)
                modificari_nume += 1
                
        for d in dirs:
            if re.search(CARACTERE_INTERZISE, d):
                cale_veche = os.path.join(root, d)
                cale_noua = generat_cale_unica_curata(cale_veche)
                if not IS_DRY_RUN:
                    os.rename(cale_veche, cale_noua)
                mesaj = f"[Folder]  {cale_veche}  -->  {os.path.basename(cale_noua)}"
                print(f"    {'[SIMULARE] ' if IS_DRY_RUN else ''}{mesaj}")
                intrari_log_redenumiri.append(mesaj)
                modificari_nume += 1

    if modificari_nume == 0:
        print("    Toate numele sunt compatibile exFAT.")

    # 1. Indexare sursă + Calcul dinamic spațiu
    print(" -> Indexare fișiere pe laptop și calcul spațiu...")
    fisiere_sursa_exacte = set()
    fisiere_sursa_dupa_hash = {}

    for root, _, files in os.walk(sursa_abs):
        for f in files:
            cale_abs = os.path.join(root, f)
            cale_rel = os.path.relpath(cale_abs, sursa_abs)
            
            fisiere_sursa_exacte.add(cale_rel)
            
            amprenta = calculeaza_hash_rapid(cale_abs)
            if amprenta:
                if amprenta not in fisiere_sursa_dupa_hash:
                    fisiere_sursa_dupa_hash[amprenta] = []
                fisiere_sursa_dupa_hash[amprenta].append(cale_rel)

            try:
                marime_sursa = os.path.getsize(cale_abs)
                cale_hdd = os.path.join(destinatia_folder, cale_rel)
                
                if not os.path.exists(cale_hdd) or os.path.getsize(cale_hdd) != marime_sursa:
                    spatiu_total_necesar_bytes += marime_sursa
            except OSError:
                pass

    # 2. Detecție mutări și ștergeri pe HDD
    print(" -> Detecție mutări și ștergeri pe HDD...")
    if os.path.exists(destinatia_folder):
        for root, _, files in os.walk(destinatia_folder):
            for f in files:
                cale_hdd_abs = os.path.join(root, f)
                cale_rel = os.path.relpath(cale_hdd_abs, destinatia_folder)
                
                if cale_rel not in fisiere_sursa_exacte:
                    amprenta_hdd = calculeaza_hash_rapid(cale_hdd_abs)
                    
                    if amprenta_hdd and amprenta_hdd in fisiere_sursa_dupa_hash and len(fisiere_sursa_dupa_hash[amprenta_hdd]) > 0:
                        cale_noua_rel = fisiere_sursa_dupa_hash[amprenta_hdd].pop(0)
                        cale_noua_hdd_abs = os.path.join(destinatia_folder, cale_noua_rel)
                        
                        if IS_DRY_RUN:
                            print(f"    [SIMULARE Mutare HDD] {cale_rel} --> {cale_noua_rel}")
                        else:
                            try:
                                os.makedirs(os.path.dirname(cale_noua_hdd_abs), exist_ok=True)
                                shutil.move(cale_hdd_abs, cale_noua_hdd_abs)
                                cale_sursa_laptop = os.path.join(sursa_abs, cale_noua_rel)
                                st = os.stat(cale_sursa_laptop)
                                os.utime(cale_noua_hdd_abs, (st.st_atime, st.st_mtime))
                            except Exception:
                                pass
                        
                        fisiere_sursa_exacte.add(cale_noua_rel)
                    else:
                        dest_sterse_abs = os.path.join(dir_sterse, cale_rel)
                        if IS_DRY_RUN:
                            print(f"    [SIMULARE Ștergere HDD] {cale_rel} --> _Fisiere_STERSE/")
                        else:
                            os.makedirs(os.path.dirname(dest_sterse_abs), exist_ok=True)
                            shutil.move(cale_hdd_abs, dest_sterse_abs)

    # Salvăm datele pentru pasul de rsync
    plan_sincronizare.append((sursa_abs, destinatia_folder, dir_modificate))

# PASUL II: VERIFICARE STRICTĂ ÎNAINTE DE RSYNC
total, used, free = shutil.disk_usage(DESTINATIA_BAZA)
marja_bytes = MARJA_SIGURANTA_MB * 1024 * 1024
necesar_total_bytes = spatiu_total_necesar_bytes + marja_bytes

spatiu_necesar_mb = spatiu_total_necesar_bytes / (1024 ** 2)
spatiu_liber_mb = free / (1024 ** 2)

print("\n" + "=" * 42)
print(f" Date noi/modificate calculate: {spatiu_necesar_mb:.2f} MB")
print(f" Spațiu liber pe HDD extern:    {spatiu_liber_mb:.2f} MB")
print("=" * 42)

if free < necesar_total_bytes:
    msg = f"Spațiu insuficient pe HDD! Date noi: {spatiu_necesar_mb:.1f} MB, Liber: {spatiu_liber_mb:.1f} MB"
    print(f"\nEROARE: {msg}")
    print("Sincronizarea A FOST OPRITĂ înainte de copiere pentru a preveni umplerea discului.")
    trimite_notificare("Backup Eșuat", msg, iconita="dialog-error")
    input("Apasă Enter pentru a închide...")
    sys.exit(1)

# PASUL III: Execuția copierii propriu-zise (doar dacă există spațiu)
for sursa_abs, destinatia_folder, dir_modificate in plan_sincronizare:
    nume_folder = os.path.basename(sursa_abs.rstrip('/'))
    print(f"\n -> Sincronizare rsync pentru {nume_folder}...")
    cmd_rsync = [
        "rsync", "-rtv", "--size-only", "--delete",
        "--info=progress2,stats2",
        f"--backup", f"--backup-dir={dir_modificate}",
        f"{sursa_abs}/", f"{destinatia_folder}/"
    ]
    
    if IS_DRY_RUN:
        cmd_rsync.append("--dry-run")
    
    for opt in EXCLUDERI:
        cmd_rsync.extend(["--exclude", opt])

    subprocess.run(cmd_rsync)

# Salvare jurnal redenumiri
if intrari_log_redenumiri and not IS_DRY_RUN:
    os.makedirs(dir_sesiune_curenta, exist_ok=True)
    with open(cale_log_redenumiri, "w", encoding="utf-8") as log_file:
        log_file.write(f"Jurnal redenumiri din {acum}\n")
        log_file.write("=" * 50 + "\n\n")
        log_file.write("\n".join(intrari_log_redenumiri))

# Curățare istoric vechi
if not IS_DRY_RUN:
    cmd_clean_empty = f'find "{DIR_ISTORIC_BAZA}/{acum}" -type d -empty -delete 2>/dev/null'
    subprocess.run(cmd_clean_empty, shell=True)

    cmd_clean_30days = f'find "{DIR_ISTORIC_BAZA}" -mindepth 1 -maxdepth 1 -type d -mtime +30 -exec rm -rf {{}} \\; 2>/dev/null'
    subprocess.run(cmd_clean_30days, shell=True)

# Notificare finalizare
if IS_DRY_RUN:
    trimite_notificare("Simulare Finalizată", "Simularea de backup s-a încheiat.")
else:
    trimite_notificare("Backup Finalizat", "Sincronizarea pe HDD-ul extern s-a încheiat cu succes!")

print("\n==========================================")
if IS_DRY_RUN:
    print("    Simulare finalizată! (Nicio modificare aplicată)")
else:
    print("    Backup finalizat cu succes!")
print("==========================================")
input("Apasă Enter pentru a închide...")
