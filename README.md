# 🚀 Smart Sync Backup Script (Linux -> exFAT)

Un script Python avansat și eficient pentru backup incremental automatizat de pe un laptop cu sistem Linux pe medii de stocare externe (HDD/SSD formatate exFAT sau NTFS).

Previne coruperea datelor, gestionează caracterele incompatibile cu exFAT, detectează mutările de fișiere prin hash și păstrează o versiune de siguranță a fișierelor modificate/șterse.

---

## ✨ Funcționalități Principale

- 🧹 **Autocurățare nume incompatibile (Pre-procesare):** Detectează și redenumește direct pe laptop fișierele/folderele care conțin caractere interzise de exFAT (`*`, `:`, `?`, `"`, `<`, `>`, `|`), prevenind erorile de scriere.
- 🛡️ **Protecție la coliziuni de nume:** În cazul numelor similare (ex: `bin*` și `bin?`), scriptul le redenumește unic (`bin_` și `bin_1`), prevenind comasarea accidentală a folderelor.
- ⚡ **Detecție inteligentă a mutărilor (Partial-Hash):** Dacă redenumești sau muți un folder mare pe laptop, scriptul detectează modificarea prin hash rapid (MD5 bazat pe dimensiune + header/footer de 64KB) și mută fișierele corespunzător pe HDD, fără a le recopia de la zero.
- 🔄 **Sincronizare 1:1 cu `rsync`:** Sincronizează doar fișierele modificate sau noi (folosind `--size-only` și potrivire de timp prin `os.utime`), afișând o bară dinamică de progres în timp real (`--info=progress2,stats2`).
- 🔒 **Detectare Read-Only & Dispozitiv Conectat:** Verifică dacă HDD-ul extern este montat corespunzător și dacă permite scrierea înainte de procesare, prevenind oprirea accidentală la jumătatea procesului.
- 📦 **Excludere automată fișiere temporare (Junk Filter):** Omite fișierele temporare sau inutile (`.tmp`, `.DS_Store`, `__pycache__`, `thumbs.db`, lock-uri LibreOffice `.~lock.*`, `.Trash-*` etc.).
- 🕒 **Istoric de siguranță (30 de zile):** Fișierele șterse sau modificate sunt salvate în folderul `_Istoric_Modificari/DATA_ORA/` timp de 30 de zile înainte de a fi curățate automat.
- 📝 **Jurnalizare (Log):** Generare automată a fișierului `redenumiri.log` pe HDD la fiecare sesiune în care au fost modificate nume din cauza caracterelor speciale exFAT.
- 💾 **Verificare spațiu liber:** Oprește execuția de siguranță dacă pe HDD-ul extern rămân mai puțin de 5 GB liberi.
- 🔔 **Notificări Desktop (Nativ Linux):** Afișează notificări pe ecran (`notify-send`) la pornire, finalizare sau în caz de eroare (HDD deconectat, spațiu insuficient, disc Read-Only).
- 🧪 **Mod Simulare (`--dry-run`):** Permite testarea completă a procesului fără a efectua nicio modificare pe disk (`python3 backup.py --dry-run`).
---

## 📋 Cerințe Sistem

- **Sistem de operare:** Linux (Ubuntu, Debian, Fedora, Arch etc.)
- **Versiune Python:** Python 3.6+
- **Pachete sistem:** `rsync`, `libnotify-bin` (pentru comanda `notify-send`)

Instalare cerințe pe sisteme Debian/Ubuntu:

<pre>
sudo apt update && sudo apt install rsync libnotify-bin python3
</pre>

---

## 🚀 Utilizare

### 1. Rulare Normală (Backup Real)
Pentru a efectua backup-ul efectiv:

<pre>
python3 backup.py
</pre>

### 2. Mod Simulare (Dry-Run)
Pentru a testa ce modificări s-ar face fără a modifica niciun fișier pe laptop sau HDD:

<pre>
python3 backup.py --dry-run
# sau
python3 backup.py -n
</pre>

---

## ⚙️ Configurare

Deschide fișierul `backup.py` și editează secțiunea de configurare de la început:

<pre>
# Căile folderelor sursă de pe laptop
FOLDERE_SURSA = [
    os.path.expanduser("~/Sync"),
    os.path.expanduser("~/Documente"),
    os.path.expanduser("~/Poze"),
]

# Calea către punctul de montare al HDD-ului extern
DESTINATIA_BAZA = "/media/UTILIZATOR/LABEL_HDD"

# Spațiul liber minim necesar pe HDD (în GB)
SPATIU_MINIM_GB = 5
</pre>

---

## 📂 Structura pe HDD Extern

După rulare, HDD-ul extern va arăta astfel:

<pre>
/media/UTILIZATOR/LABEL_HDD/
├── Documente/               &lt;-- Copia fidelă
├── Poze/                    &lt;-- Copia fidelă
├── Sync/                    &lt;-- Copia fidelă
└── _Istoric_Modificari/
    └── 2026-09-06_12-00/    &lt;-- Folderul sesiunii curente
        ├── redenumiri.log   &lt;-- Jurnalul de redenumiri (dacă au existat)
        ├── _Fisiere_STERSE/ &lt;-- Fișiere eliminate de pe laptop
        └── _Fisiere_MODIFICATE/ &lt;-- Versiuni vechi ale fișierelor editate
</pre>
## 📊 Comparație cu alte soluții populare de backup

Deși există multe programe de backup pe Linux, majoritatea întâmpină probleme serioase pe un disc extern formatat **exFAT** sau creează arhive opace care nu pot fi citite direct pe alte dispozitive. 

Scriptul `backup.py` a fost dezvoltat special pentru a elimina aceste neajunsuri:

| Criteriu / Funcționalitate | Borg / Restic | FreeFileSync | Rclone | Syncthing | **Scriptul Tău (`backup.py`)** |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Format date pe HDD** | Arhivă opacă / criptată | Fișiere normale (1:1) | Fișiere normale (1:1) | Fișiere normale (1:1) | **Fișiere normale (1:1)** |
| **Acces direct (Windows / Mac / TV)** | ❌ Nu (necesită soft) | ✅ Da | ✅ Da | ✅ Da | ✅ **Da (Direct de pe disc)** |
| **Compatibilitate exFAT pe Linux** | ❌ Incompatibil (necesită POSIX) | ⚠️ Fără redenumire automată | ⚠️ Fără sanitizare prealabilă | ❌ Eroare permisiuni / caractere | ✅ **Nativă (Curățare automatizată)** |
| **Detecție redenumiri / mutări** | ✅ Da (Deduplicare) | ✅ Da | ⚠️ Doar cu `--track-renames` | ✅ Da (Sincronizare live) | ✅ **Partial-Hash ultra-rapid** |
| **Gestiune HDD USB detașabil** | ⚠️ Necesită scriptare extra | ⚠️ Necesită fișiere XML | ⚠️ Manual / prin CLI | ❌ Conceput pentru dispozitive live | ✅ **Optimizat (Notificări + Oprire curată)** |
| **Verificare Read-Only & Spațiu** | ❌ Nu | ❌ Nu | ❌ Nu | ❌ Nu | ✅ **Integrată nativ (cu notificare)** |
| **Notificări Desktop (D-Bus / XDG)** | ❌ Necesită wrapper | ⚠️ Parțial | ❌ Nu | ⚠️ Doar prin interfața web | ✅ **Integrat nativ (`notify-send`)** |
| **Impact resurse sistem** | Minim (doar la rulare) | Mediu (interfață GUI) | Minim (doar la rulare) | ❌ Permanent în fundal (RAM/CPU) | ✅ **Zero resurse (rulează doar la cerere)** |
| **Istoric modificări (Versioning)** | ✅ Da (în arhivă) | ✅ Da (opțional) | ⚠️ Cu opțiunea `--backup-dir` | ⚠️ Opțiuni limitate | ✅ **Da (30 de zile automatizat)** |

### De ce este `backup.py` soluția optimă pentru acest scenariu?

1. **Elimină blocajele exFAT:** Spre deosebire de alte unelte care se opresc cu eroare când întâlnesc caractere speciale (`:`, `?`, `*`) sau permisiuni POSIX necompatibile, `backup.py` curăță numele fișierelor pe laptop **înainte** de copiere.
2. **Transparență 1:1:** Fișierele sunt salvate în format nativ, fiind accesibile instant pe orice calculator sau televizor, fără a depinde de o aplicație terță de restaurare.
3. **Pachet integrat de protecție:** Validează dacă discul este montat *Read-Only*, verifică spațiul liber rămas (minim 5 GB), procesează mutările eficient prin Partial-Hash și trimite notificări vizuale pe ecran la fiecare etapă.
