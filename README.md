  🚀 Smart Sync Backup Script (Linux -> exFAT) :root { --bg-color: #0f172a; --card-bg: #1e293b; --text-color: #f8fafc; --text-muted: #94a3b8; --accent-color: #38bdf8; --code-bg: #0f172a; --border-color: #334155; --warning-color: #f59e0b; } body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: var(--bg-color); color: var(--text-color); line-height: 1.6; margin: 0; padding: 20px; } .container { max-width: 900px; margin: 0 auto; background: var(--card-bg); padding: 40px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3); border: 1px solid var(--border-color); } h1 { color: #ffffff; border-bottom: 2px solid var(--border-color); padding-bottom: 12px; margin-top: 0; font-size: 1.8em; } h2 { color: #ffffff; margin-top: 30px; border-bottom: 1px solid var(--border-color); padding-bottom: 8px; font-size: 1.3em; } h3 { color: var(--text-color); font-size: 1.1em; margin-top: 20px; } p, li { color: var(--text-color); } ul, ol { padding-left: 20px; } ul.features-list { list-style: none; padding-left: 0; } ul.features-list li { background-color: var(--code-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 12px 16px; margin-bottom: 12px; } ul.features-list strong { color: var(--accent-color); } code { background-color: var(--code-bg); color: var(--accent-color); padding: 3px 6px; border-radius: 4px; font-family: "Fira Code", Monaco, Consolas, "Courier New", monospace; font-size: 0.9em; border: 1px solid var(--border-color); } pre { background-color: var(--code-bg); padding: 16px; border-radius: 8px; overflow-x: auto; border: 1px solid var(--border-color); } pre code { background-color: transparent; padding: 0; border: none; color: #e2e8f0; } hr { border: none; border-top: 1px solid var(--border-color); margin: 30px 0; } .note { font-style: italic; color: var(--text-muted); }

🚀 Smart Sync Backup Script (Linux -> exFAT)
============================================

Un script Python pentru backup incremental automatizat de pe un laptop cu sistem Linux pe medii de stocare externe (HDD/SSD formatate exFAT sau NTFS).

Previne coruperea datelor, gestionează caracterele incompatibile cu exFAT, detectează mutările de fișiere prin hash și păstrează o versiune de siguranță a fișierelor modificate/șterse.

* * *

✨ Funcționalități Principale
----------------------------

*   🧹 **Autocurățare nume incompatibile (Pre-procesare):** Detectează și redenumește direct pe laptop fișierele/folderele care conțin caractere interzise de exFAT (`*`, `:`, `?`, `"`, `<`, `>`, `|`), prevenind erorile de scriere.
*   🛡️ **Protecție la coliziuni de nume:** În cazul numelor similare (ex: `bin*` și `bin?`), scriptul le redenumește unic (`bin_` și `bin_1`), prevenind comasarea accidentală a folderelor.
*   ⚡ **Detecție inteligentă a mutărilor (Partial-Hash):** Dacă redenumești sau muți un folder mare pe laptop, scriptul detectează modificarea prin hash rapid (MD5 bazat pe dimensiune + header/footer de 64KB) și mută fișierele corespunzător pe HDD, fără a le recopia de la zero.
*   🔄 **Sincronizare 1:1 cu rsync:** Sincronizează doar fișierele modificate sau noi (folosind `--size-only` și potrivire de timp prin `os.utime`), afișând o bară dinamică de progres în timp real (`--info=progress2,stats2`).
*   🔒 **Detectare Read-Only & Dispozitiv Conectat:** Verifică dacă HDD-ul extern este montat corespunzător și dacă permite scrierea înainte de procesare, prevenind oprirea accidentală la jumătatea procesului.
*   📦 **Excludere automată fișiere temporare (Junk Filter):** Omite fișierele temporare sau inutile (`.tmp`, `.DS_Store`, `__pycache__`, `thumbs.db`, lock-uri LibreOffice `.~lock.*`, `.Trash-*` etc.).
*   🕒 **Istoric de siguranță (30 de zile):** Fișierele șterse sau modificate sunt salvate în folderul `_Istoric_Modificari/DATA_ORA/` timp de 30 de zile înainte de a fi curățate automat.
*   📝 **Jurnalizare (Log):** Generare automată a fișierului `redenumiri.log` pe HDD la fiecare sesiune în care au fost modificate nume din cauza caracterelor speciale exFAT.
*   💾 **Verificare dinamică a spațiului liber:** Calculează dimensiunea exactă a datelor noi sau modificate și oprește execuția de siguranță ÎNAINTE de transfer dacă spațiul liber de pe HDD este insuficient (include o marjă minimă de siguranță de 200 MB), prevenind erorile la jumătatea procesului.
*   🔔 **Notificări Desktop (Nativ Linux):** Afișează notificări pe ecran (`notify-send`) la pornire, finalizare sau în caz de eroare (HDD deconectat, spațiu insuficient, disc Read-Only).
*   🧪 **Mod Simulare (--dry-run):** Permite testarea completă a procesului fără a efectua nicio modificare pe disk (`python3 backup.py /sursa /destinatie --dry-run`).

* * *

🚀 Cerințe de Sistem
--------------------

*   **Sistem de Operare**: Linux (Ubuntu, Debian, Fedora, Arch, Linux Mint, etc.)
*   **Utilitare Necesare**: `python3`, `rsync`, `notify-send` (`libnotify-bin`)

Pentru instalarea dependențelor pe sisteme bazate pe Debian/Ubuntu:

    sudo apt update
    sudo apt install python3 rsync libnotify-bin

* * *

🛠️ Utilizare
-------------

Scriptul primește căile **sursă** ca primii parametri, iar **ultimul parametru** furnizat va fi întotdeauna calea către **destinație** (HDD-ul/stick-ul extern).

### Sintaxă:

    ./backup.py <sursa1> [sursa2 ...] <destinatie> [opțiuni]

### Exemple:

**1\. Backup pentru un singur folder:**

    ./backup.py ~/Documents /media/dan/stick

**2\. Backup pentru directoare multiple de pe laptop:**

    ./backup.py ~/Desktop ~/Documents ~/Downloads /media/dan/stick

**3\. Rulare în mod Simulare (Dry-Run):**

Afișează toate operațiunile (sanitizări, mutări, sincronizări rsync) fără a scrie sau șterge fizic pe disc.

    ./backup.py ~/Desktop ~/Documents ~/Downloads /media/dan/stick --dry-run

_Notă:_ Puteți folosi și scurtătura `-n`:

    ./backup.py ~/Documents /media/dan/stick -n

* * *

📂 Structura Generată pe HDD
----------------------------

Destinația va avea următoarea structură curată:

    /media/dan/stick/
    ├── Desktop/                       <-- Sincronizare directă folder
    ├── Documents/                     <-- Sincronizare directă folder
    ├── Downloads/                     <-- Sincronizare directă folder
    └── _Istoric_Modificari/
        └── 2026-03-09_18-30/          <-- Folderul sesiunii curente
            ├── redenumiri.log         <-- Jurnalul redenumirilor de pe laptop
            ├── _Fisiere_STERSE/        <-- Fișierele șterse de pe laptop
            └── _Fisiere_MODIFICATE/    <-- Versiunile vechi ale fișierelor modificate

* * *

🔧 Permisiuni de Execuție
-------------------------

Pentru a rula scriptul direct, asigurați-vă că are drepturi de execuție:

    chmod +x backup.py
