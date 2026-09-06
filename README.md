# 🚀 Smart Sync Backup Script (Linux -> exFAT)

Un script Python pentru backup incremental automatizat de pe un laptop cu sistem Linux pe medii de stocare externe (HDD/SSD formatate exFAT sau NTFS).

Previne coruperea datelor, gestionează caracterele incompatibile cu exFAT, detectează mutările de fișiere prin hash și păstrează o versiune de siguranță a fișierelor modificate/șterse.

---

## ✨ Funcționalități Principale

* 🧹 **Autocurățare nume incompatibile (Pre-procesare):** Detectează și redenumește direct pe laptop fișierele/folderele care conțin caractere interzise de exFAT (`*`, `:`, `?`, `"`, `<`, `>`, `|`), prevenind erorile de scriere.
* 🛡️ **Protecție la coliziuni de nume:** În cazul numelor similare (ex: `bin*` și `bin?`), scriptul le redenumește unic (`bin_` și `bin_1`), prevenind comasarea accidentală a folderelor.
* ⚡ **Detecție inteligentă a mutărilor (Partial-Hash):** Dacă redenumești sau muți un folder mare pe laptop, scriptul detectează modificarea prin hash rapid (MD5 bazat pe dimensiune + header/footer de 64KB) și mută fișierele corespunzător pe HDD, fără a le recopia de la zero.
- 🔄 **Sincronizare 1:1 cu rsync:** Sincronizează doar fișierele modificate sau noi, afișând o bară dinamică de progres în timp real (`--info=progress2,stats2`).
* 🔒 **Detectare Read-Only & Dispozitiv Conectat:** Verifică dacă HDD-ul extern este montat corespunzător și dacă permite scrierea înainte de procesare, prevenind oprirea accidentală la jumătatea procesului.
* 📦 **Excludere automată fișiere temporare (Junk Filter):** Omite fișierele temporare sau inutile (`.tmp`, `.DS_Store`, `__pycache__`, `thumbs.db`, lock-uri LibreOffice `.~lock.*`, `.Trash-*` etc.).
* 🕒 **Istoric de siguranță (30 de zile):** Fișierele șterse sau modificate sunt salvate în folderul `_Istoric_Modificari/DATA_ORA/` timp de 30 de zile înainte de a fi curățate automat.
* 📝 **Jurnalizare (Log):** Generare automată a fișierului `redenumiri.log` pe HDD la fiecare sesiune în care au fost modificate nume din cauza caracterelor speciale exFAT.
* 💾 **Verificare dinamică a spațiului liber:** Calculează dimensiunea exactă a datelor noi sau modificate și oprește execuția de siguranță ÎNAINTE de transfer dacă spațiul liber de pe HDD este insuficient (include o marjă minimă de siguranță de 200 MB), prevenind erorile la jumătatea procesului.
* 🔔 **Notificări Desktop (Nativ Linux):** Afișează notificări pe ecran (`notify-send`) la pornire, finalizare sau în caz de eroare (HDD deconectat, spațiu insuficient, disc Read-Only).
* 🧪 **Mod Simulare (--dry-run):** Permite testarea completă a procesului fără a efectua nicio modificare pe disk (`python3 backup.py /sursa /destinatie --dry-run`).

---

## 🚀 Cerințe de Sistem

- **Sistem de Operare:** Linux (Ubuntu, Arch etc.) - curent optional 😁
- **Utilitare Necesare:** `python3`, `rsync`, `notify-send` (`libnotify-bin`), `find` (`findutils`)

Pentru instalarea dependențelor pe sisteme bazate pe Debian/Ubuntu:
```bash
sudo apt update
sudo apt install python3 rsync libnotify-bin findutils
```

---

## 🛠️ Utilizare

Scriptul primește căile **sursă** ca primii parametri, iar **ultimul parametru** furnizat va fi întotdeauna calea către **destinație** (HDD-ul/stick-ul extern).

### Sintaxă:
```bash
./backup.py <sursa1> [sursa2 ...] <destinatie> [opțiuni]
```

### Exemple:

1. **Backup pentru un singur folder:**
   ```bash
   ./backup.py ~/Documents /media/dan/stick
   ```

2. **Backup pentru directoare multiple de pe laptop:**
   ```bash
   ./backup.py ~/Desktop ~/Documents ~/Downloads /media/dan/stick
   ```

3. **Rulare în mod Simulare (Dry-Run):**
   Afișează toate operațiunile (sanitizări, mutări, sincronizări rsync) fără a scrie sau șterge fizic pe disc.
   ```bash
   ./backup.py ~/Desktop ~/Documents ~/Downloads /media/dan/stick --dry-run
   ```
   *Notă:* Puteți folosi și scurtătura `-n`:
   ```bash
   ./backup.py ~/Documents /media/dan/stick -n
   ```

---

## 📂 Structura Generată pe HDD

Destinația va avea următoarea structură curată:

```text
/media/dan/stick/
├── Desktop/                       <-- Sincronizare directă folder
├── Documents/                     <-- Sincronizare directă folder
├── Downloads/                     <-- Sincronizare directă folder
└── _Istoric_Modificari/
    └── 2026-03-09_18-30/          <-- Folderul sesiunii curente
        ├── redenumiri.log         <-- Jurnalul redenumirilor de pe laptop
        ├── _Fisiere_STERSE/        <-- Fișierele șterse de pe laptop
        └── _Fisiere_MODIFICATE/    <-- Versiunile vechi ale fișierelor modificate
```

