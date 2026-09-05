# 🚀 Smart Sync Backup Script (Linux -> exFAT)

Un script Python avansat și eficient pentru backup incremental automatizat de pe un laptop cu sistem Linux pe medii de stocare externe (HDD/SSD formatate exFAT sau NTFS).

Previne coruperea datelor, gestionează caracterele incompatibile cu exFAT, detectează mutările de fișiere prin hash și păstrează o versiune de siguranță a fișierelor modificate/șterse.

---

## ✨ Funcționalități Principale

- 🧹 **Autocurățare nume incompatibile (Pre-procesare):** Detectează și redenumește direct pe laptop fișierele/folderele care conțin caractere interzise de exFAT (`*`, `:`, `?`, `"`, `<`, `>`, `|`), prevenind erorile de scriere.
- 🛡️ **Protecție la coliziuni de nume:** În cazul numelor similare (ex: `bin*` și `bin?`), scriptul le redenumește unic (`bin_` și `bin_1`), prevenind comasarea accidentală a folderelor.
- ⚡ **Detecție inteligentă a mutărilor (Partial-Hash):** Dacă redenumești sau muți un folder mare pe laptop, scriptul detectează modificarea prin hash rapid (MD5 bazat pe dimensiune + header/footer de 64KB) și mută fișierele corespunzător pe HDD, fără a le recopia de la zero.
- 🔄 **Sincronizare 1:1 cu `rsync`:** Sincronizează doar fișierele modificate sau noi (folosind `--size-only` și potrivire de timp prin `os.utime`), afișând o bară dinamică de progres în timp real (`--info=progress2,stats2`).
- 📦 **Excludere automată fișiere temporare (Junk Filter):** Omite fișierele temporare sau inutile (`.tmp`, `.DS_Store`, `__pycache__`, `thumbs.db`, lock-uri LibreOffice `.~lock.*`, `.Trash-*` etc.).
- 🕒 **Istoric de siguranță (30 de zile):** Fișierele șterse sau modificate sunt salvate în folderul `_Istoric_Modificari/DATA_ORA/` timp de 30 de zile înainte de a fi curățate automat.
- 📝 **Jurnalizare (Log):** Generare automată a fișierului `redenumiri.log` pe HDD la fiecare sesiune în care au fost modificate nume din cauza caracterelor speciale exFAT.
- 💾 **Verificare spațiu liber:** Oprește execuția de siguranță dacă pe HDD-ul extern rămân mai puțin de 5 GB liberi.
- 🔔 **Notificări Desktop (Nativ Linux):** Afișează notificări pe ecran (`notify-send`) la pornire, finalizare sau în caz de eroare (HDD deconectat, spațiu insuficient).
- 🧪 **Mod Simulare (`--dry-run`):** Permite testarea completă a procesului fără a efectua nicio modificare pe disk (`python3 backup.py --dry-run`).

---

## 📋 Cerințe Sistem

- **Sistem de operare:** Linux (Ubuntu, Debian, Fedora, Arch etc.)
- **Versiune Python:** Python 3.6+
- **Pachete sistem:** `rsync`, `libnotify-bin` (pentru comanda `notify-send`)

Instalare cerințe pe sisteme Debian/Ubuntu:
```bash
sudo apt update && sudo apt install rsync libnotify-bin python3
