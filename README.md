# 🔄 backup.py — Backup inteligent Linux → exFAT

Script Python pentru sincronizare incrementală a folderelor importante de pe
Linux către un HDD/stick extern formatat exFAT, cu detecție de fișiere
mutate/redenumite, istoric al versiunilor vechi și verificări de siguranță
înainte de orice modificare pe disc.

Nu e un simplu wrapper peste `rsync` — indexează sursa, detectează ce s-a
mutat vs. ce s-a șters cu adevărat, verifică spațiul disponibil **înainte**
de a atinge discul, și păstrează un istoric per-sesiune al fișierelor
suprascrise sau șterse.

---

## ✨ Funcționalități

- **Sincronizare incrementală** cu `rsync`, comparând `mtime + size`, cu
  toleranță `--modify-window=2` pentru precizia de timp de 2 secunde a
  exFAT.
- **Detecție de mutări/redenumiri** — dacă un fișier a fost mutat sau
  redenumit în sursă, scriptul îl recunoaște după conținut (hash) și îl
  mută în locul corespunzător pe HDD, în loc să-l copieze din nou.
- **Istoric al versiunilor** — fișierele modificate sau șterse din sursă nu
  se pierd: ajung în `_Istoric/.../<sesiune>/_MODIF` respectiv `_STERS`,
  organizate per utilizator și per sesiune de backup.
- **Autocurățare nume incompatibile cu exFAT/Windows** — caractere
  interzise (`\ : * ? " < > |`), nume rezervate (`CON`, `PRN`, `COM1`...),
  spații/puncte la final — sunt corectate automat pe sursă, cu jurnal al
  redenumirilor.
- **Protecție la coliziuni de nume** — dacă după curățare două nume ar
  ajunge identice (ex. `bin*` și `bin?` devin ambele `bin_`), scriptul le
  face unice automat (`bin_`, `bin_1`, ...), ca să nu se comaseze
  accidental două fișiere sau foldere diferite.
- **Excludere automată a fișierelor/folderelor temporare (junk filter)** —
  nu sunt sincronizate niciodată fișierele gen `*.tmp`, `*~`,
  `.~lock.*` (lock-uri LibreOffice), `*.part`, `*.crdownload`,
  `thumbs.db`, `.DS_Store`, `desktop.ini`, respectiv folderele
  `__pycache__`, `.pytest_cache`, `.thumbnails`, `.Trash-*`,
  `$RECYCLE.BIN`, `System Volume Information`.
- **Verificare de spațiu înainte de sincronizare** — calculează exact câți
  MB sunt necesari (inclusiv spațiul păstrat pentru versiunile vechi) și
  oprește totul dacă nu încape, **fără să atingă discul**.
- **Verificări de siguranță** — refuză să ruleze ca root, verifică dacă
  discul e montat și scriibil, și blochează suprapunerile periculoase
  între surse și destinație (ex. destinația aflată în interiorul unei
  surse, ceea ce ar cauza copiere recursivă).
- **Mod simulare (`--dry-run`)** — arată exact ce s-ar întâmpla, fără nicio
  modificare fizică.
- **Notificări desktop** (via `notify-send`) la început și la final.
- **Curățare automată a istoricului vechi** (configurabil, implicit 30 de
  zile).

---

## 📋 Cerințe

- Linux (testat pe Linux Mint)
- Python 3.8+
- `rsync` instalat
- `notify-send` (opțional — notificările sunt dezactivate automat dacă
  lipsește)

Nu necesită niciun pachet Python în afara bibliotecii standard.

---

## 🚀 Utilizare

```bash
./backup.py sursa1 [sursa2 ...] destinatie [opțiuni]
```

Ultimul argument e întotdeauna destinația; toate celelalte sunt foldere
sursă.

### Exemple

```bash
# Backup simplu, un singur folder
./backup.py ~/Documents /media/dan/stick

# Mai multe surse într-o singură rulare
./backup.py ~/Desktop ~/Documents ~/Poze /media/dan/stick

# Simulare — vezi ce s-ar întâmpla, fără modificări reale
./backup.py ~/Documents /media/dan/stick --dry-run

# Output detaliat, fișier cu fișier + bară de progres live
./backup.py ~/Documents /media/dan/stick --verbose
```

Cu `--verbose`, `rsync` rulează cu `--info=progress2,stats2,name` și arată
o bară de progres live pe fișier transferat; fără `--verbose`, output-ul e
mai concis (doar numele fișierelor + statistici finale).

### Opțiuni

| Opțiune | Descriere | Implicit |
|---|---|---|
| `-n`, `--dry-run` | Simulare, fără nicio modificare fizică | — |
| `-v`, `--verbose` | Listare completă a fișierelor procesate de rsync | — |
| `--marja-mb MB` | Marjă de siguranță suplimentară la verificarea de spațiu | `200` |
| `--zile-istoric N` | Câte zile se păstrează sesiunile vechi din istoric | `30` |

---

## 🗂️ Structura pe destinație

```
/media/dan/stick/
├── home/dan/Documents/...          <- backup curent (oglindă a căii sursă)
├── home/dan/Desktop/...
└── _Istoric/
    └── home/dan/                   <- istoric separat per utilizator
        └── 2026-09-10_14-30-05/
            ├── _MODIF/...          <- versiunile vechi ale fișierelor suprascrise
            ├── _STERS/...          <- fișiere șterse din sursă
            └── redenumiri.log      <- jurnal al numelor corectate pt. exFAT
```

Fiecare sursă e oglindită pe destinație după calea ei absolută completă —
nu doar după numele folderului — astfel încât două surse cu același nume
de bază (ex. `~/Documents` și `/media/extern/Documents`) nu se suprapun
niciodată pe backup.

---

## ⚙️ Cum funcționează, pe scurt

1. **Planificare (read-only)** — pentru fiecare sursă: se corectează
   numele incompatibile cu exFAT, se indexează toate fișierele (cu un hash
   rapid pe conținut, pentru detecția mutărilor) și se calculează spațiul
   necesar, folosind exact aceeași logică de comparație pe care o va
   folosi `rsync` (`mtime + size`, toleranță 2 secunde).
2. **Verificare de spațiu** — se însumează necesarul pentru toate sursele
   și se compară cu spațiul liber + marja de siguranță. Dacă nu e
   suficient, scriptul se oprește aici — **nimic nu a fost încă modificat
   pe HDD**.
3. **Execuție** — abia acum se ating date pe disc: fișierele mutate/
   redenumite în sursă sunt mutate corespunzător pe HDD (nu recopiate),
   cele dispărute din sursă sunt relocate în `_STERS`, apoi `rsync`
   sincronizează conținutul propriu-zis, păstrând versiunile suprascrise
   în `_MODIF`.

---

## ⚠️ De reținut

- Scriptul **redenumește fișierele originale de pe sursă** (nu doar
  copiile de pe backup) dacă acestea au caractere incompatibile cu
  exFAT/Windows. Redenumirile sunt jurnalizate în `redenumiri.log`.
- Nu rulați scriptul cu `sudo`/ca root — refuză explicit acest lucru.
- Codurile de eroare `rsync` 23/24 (fișiere modificate/dispărute în timpul
  transferului) sunt tratate ca avertismente, nu ca eșec total — se pot
  întâmpla normal dacă lucrați în fișiere în timp ce rulează backup-ul.

---

## 📄 Licență

GPL-3.0
