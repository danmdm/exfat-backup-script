#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys
import hashlib
import re
from datetime import datetime

# --- CONFIGURARE LISTĂ FOLDERE SURSĂ ---
FOLDERE_SURSA = [
    os.path.expanduser("~/Sync"),
    os.path.expanduser("~/Documente"),
    os.path.expanduser("~/Poze"),
]

# --- CONFIGURARE HDD EXTERN ---
DESTINATIA_BAZA = "/media/dan/7FBC-FE02"
DIR_ISTORIC_BAZA = os.path.join(DESTINATIA_BAZA, "_Istoric_Modificari")
SPATIU_MINIM_GB = 5  # Limită de siguranță pentru spațiul liber

CARACTERE_INTERZISE = r'[\\:*?\"<>|]'

def generat_cale_unica_curata(cale_veche):
    """
    Curăță numele fișierului/folderului și garantează un nume unic
    dacă există o coliziune (ex: bin* și bin? -> bin_ și bin_1).
    """
    cale_dir, nume_vechi = os.path.split(cale_veche)
    nume_curat = re.sub(CARACTERE_INTERZISE, '_', nume_vechi).strip('.')
    
    # Dacă nu conține caractere interzise, returnăm calea originală
    if nume_curat == nume_vechi:
        return cale_veche
        
    cale_noua = os.path.join(cale_dir, nume_curat)
    
    # Rezolvare coliziuni: dacă bin_ există deja, generează bin_1, bin_2 etc.
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

# Verificare conexiune HDD
if not os.path.exists(DESTINATIA_BAZA):
    print("==========================================")
    print("EROARE: HDD-ul extern nu este conectat!")
    print("==========================================")
    input("Apasă Enter pentru a închide...")
    sys.exit(1)

# --- VERIFICARE SPAȚIU DISPONIBIL ---
total, used, free = shutil.disk_usage(DESTINATIA_BAZA)
spatiu_liber_gb = free / (1024 ** 3)

if spatiu_liber_gb < SPATIU_MINIM_GB:
    print("==========================================")
    print(f"EROARE: Spațiu insuficient pe HDD-ul extern!")
    print(f"Spațiu liber rămas: {spatiu_liber_gb:.2f} GB (Minim necesar: {SPATIU_MINIM_GB} GB)")
    print("==========================================")
    input("Apasă Enter pentru a închide...")
    sys.exit(1)

acum = datetime.now().strftime("%Y-%m-%d_%H-%M")
dir_sesiune_curenta = os.path.join(DIR_ISTORIC_BAZA, acum)
dir_sterse_sesiune = os.path.join(dir_sesiune_curenta, "_Fisiere_STERSE")
dir_modificate_sesiune = os.path.join(dir_sesiune_curenta, "_Fisiere_MODIFICATE")
cale_log_redenumiri = os.path.join(dir_sesiune_curenta, "redenumiri.log")

print("==========================================")
print(f"   Incepe backup-ul inteligent (Spațiu liber: {spatiu_liber_gb:.1f} GB)...")
print("==========================================")

def calculeaza_hash_rapid(cale_fisier):
    """Calculează un hash rapid bazat pe mărime + primii 64KB + ultimii 64KB."""
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

intrari_log_redenumiri = []

# Procesăm fiecare folder din listă
for sursa_abs in FOLDERE_SURSA:
    if not os.path.exists(sursa_abs):
        print(f"\n[Avertisment] Folderul sursă nu există: {sursa_abs} (se omite)")
        continue

    nume_folder = os.path.basename(sursa_abs.rstrip('/'))
    destinatia_folder = os.path.join(DESTINATIA_BAZA, nume_folder)
    dir_sterse = os.path.join(dir_sterse_sesiune, nume_folder)
    dir_modificate = os.path.join(dir_modificate_sesiune, nume_folder)

    print(f"\n---> Procesare folder: {nume_folder} <---")

    # 0. PRE-PROCESARE: Redenumire automată cu protecție la coliziuni pe laptop
    print(" -> Autocurățare nume incompatibile pe laptop...")
    modificari_nume = 0
    for root, dirs, files in os.walk(sursa_abs, topdown=False):
        for f in files:
            if re.search(CARACTERE_INTERZISE, f):
                cale_veche = os.path.join(root, f)
                cale_noua = generat_cale_unica_curata(cale_veche)
                os.rename(cale_veche, cale_noua)
                
                mesaj = f"[Fișier]  {cale_veche}  -->  {os.path.basename(cale_noua)}"
                print(f"    {mesaj}")
                intrari_log_redenumiri.append(mesaj)
                modificari_nume += 1
                
        for d in dirs:
            if re.search(CARACTERE_INTERZISE, d):
                cale_veche = os.path.join(root, d)
                cale_noua = generat_cale_unica_curata(cale_veche)
                os.rename(cale_veche, cale_noua)
                
                mesaj = f"[Folder]  {cale_veche}  -->  {os.path.basename(cale_noua)}"
                print(f"    {mesaj}")
                intrari_log_redenumiri.append(mesaj)
                modificari_nume += 1

    if modificari_nume > 0:
        print(f"    S-au redenumit automat {modificari_nume} elemente pe laptop.")
    else:
        print("    Toate numele sunt compatibile exFAT.")

    # 1. Indexare sursă (Laptop)
    print(" -> Indexare fișiere pe laptop...")
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

    # 2. Detecție mutări și ștergeri pe HDD
    print(" -> Detecție mutări și ștergeri pe HDD...")
    if os.path.exists(destinatia_folder):
        for root, _, files in os.walk(destinatia_folder):
            for f in files:
                cale_hdd_abs = os.path.join(root, f)
                cale_rel = os.path.relpath(cale_hdd_abs, destinatia_folder)
                
                if cale_rel not in fisiere_sursa_exacte:
                    amprenta_hdd = calculeaza_hash_rapid(cale_hdd_abs)
                    
                    # Mutat / Redenumit (potrivire 1:1 prin Hash)
                    if amprenta_hdd and amprenta_hdd in fisiere_sursa_dupa_hash and len(fisiere_sursa_dupa_hash[amprenta_hdd]) > 0:
                        cale_noua_rel = fisiere_sursa_dupa_hash[amprenta_hdd].pop(0)
                        cale_noua_hdd_abs = os.path.join(destinatia_folder, cale_noua_rel)
                        
                        try:
                            os.makedirs(os.path.dirname(cale_noua_hdd_abs), exist_ok=True)
                            shutil.move(cale_hdd_abs, cale_noua_hdd_abs)
                            
                            # Sincronizăm timestamp-ul de pe laptop pe HDD
                            cale_sursa_laptop = os.path.join(sursa_abs, cale_noua_rel)
                            st = os.stat(cale_sursa_laptop)
                            os.utime(cale_noua_hdd_abs, (st.st_atime, st.st_mtime))
                        except Exception:
                            pass
                        
                        fisiere_sursa_exacte.add(cale_noua_rel)
                    
                    # Șters definitiv de pe laptop
                    else:
                        dest_sterse_abs = os.path.join(dir_sterse, cale_rel)
                        os.makedirs(os.path.dirname(dest_sterse_abs), exist_ok=True)
                        shutil.move(cale_hdd_abs, dest_sterse_abs)

    # 3. Sincronizare rsync (oglindă curată)
    print(" -> Sincronizare și salvare versiuni modificate...")
    cmd_rsync = [
        "rsync", "-rtv", "--size-only", "--delete",
        f"--backup", f"--backup-dir={dir_modificate}",
        f"{sursa_abs}/", f"{destinatia_folder}/"
    ]
    subprocess.run(cmd_rsync)

# Salvare jurnal de redenumiri pe HDD extern dacă au existat modificări
if intrari_log_redenumiri:
    os.makedirs(dir_sesiune_curenta, exist_ok=True)
    with open(cale_log_redenumiri, "w", encoding="utf-8") as log_file:
        log_file.write(f"Jurnal redenumiri din {acum}\n")
        log_file.write("=" * 50 + "\n\n")
        log_file.write("\n".join(intrari_log_redenumiri))
    print(f"\n[Info] Jurnalul de redenumiri a fost salvat pe HDD în:\n       {cale_log_redenumiri}")

# 4. Curățare directoare goale din istoric
cmd_clean_empty = f'find "{DIR_ISTORIC_BAZA}/{acum}" -type d -empty -delete 2>/dev/null'
subprocess.run(cmd_clean_empty, shell=True)

# 5. Curățare istoric mai vechi de 30 de zile
cmd_clean_30days = f'find "{DIR_ISTORIC_BAZA}" -mindepth 1 -maxdepth 1 -type d -mtime +30 -exec rm -rf {{}} \\; 2>/dev/null'
subprocess.run(cmd_clean_30days, shell=True)

print("\n==========================================")
print("   Backup finalizat cu succes!")
print("==========================================")
input("Apasă Enter pentru a închide...")
