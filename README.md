# exfat-backup-script
# Linux to exFAT Smart Backup Script

Script Python pentru backup automatizat și sincronizare 1:1 de pe un laptop cu sistem Linux pe un HDD extern formatat **exFAT/FAT32**.

## 🚀 Caracteristici

- **Autocurățare nume incompatibile (Pre-procesare):** Detectează și redenumeste direct pe laptop fișierele/folderele care conțin caractere interzise de exFAT (`*`, `:`, `?`, `"`, `<`, `>`, `|`), prevenind erorile de scriere.
- **Protecție la coliziuni de nume:** În cazul numelor similare (ex: `bin*` și `bin?`), scriptul le redenumește unic (`bin_` și `bin_1`), prevenind comasarea accidentală a folderelor.
- **Detecție inteligentă a mutărilor (Partial-Hash):** Dacă redenumești sau muți un folder mare pe laptop, scriptul detectează modificarea prin hash rapid (MD5 pe dimensiune + header/footer 64KB) și mută fișierele corespunzător pe HDD, fără a le recopia de la zero.
- **Sincronizare 1:1 cu `rsync`:** Sincronizează doar fișierele modificate sau noi (folosind `--size-only` și potrivire de timp `os.utime`).
- **Istoric de siguranță (30 de zile):** Fișierele șterse sau modificate sunt salvate în folderul `_Istoric_Modificari/DATA_ORA/` timp de 30 de zile înainte de a fi curățate automat.
- **Jurnalizare (Log):** Generare automată a fișierului `redenumiri.log` pe HDD la fiecare sesiune în care au fost modificate nume.
- **Verificare spațiu liber:** Oprește execuția dacă pe HDD-ul extern rămân mai puțin de 5 GB liberi.

## 📋 Cerințe sistem

- **Sistem de operare:** Linux (Ubuntu/Debian, Fedora, Arch etc.)
- **Python:** version 3.6+
- **Dependențe sistem:** `rsync`

```bash
sudo apt update && sudo apt install rsync python3
