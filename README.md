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
