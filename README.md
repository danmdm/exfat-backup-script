# backup_exfat.py

Script de backup inteligent pentru Linux, care sincronizează foldere locale pe un stick/HDD extern formatat exFAT, cu detecție de mutări/redenumiri, protecție împotriva ștergerilor accidentale în masă și istoric al fișierelor modificate/șterse.

## Caracteristici

- **Sincronizare cu `rsync`** (recursiv, păstrează timpii de modificare).
- **Detecție mutări/redenumiri**: dacă un fișier a fost mutat sau redenumit pe laptop, scriptul îl recunoaște după conținut (hash) pe stick și îl mută, în loc să-l copieze din nou și să lase o copie orfană.
- **Istoric, nu ștergere definitivă**: fișierele șterse sau modificate pe laptop nu sunt eliminate de pe stick, ci mutate în `_Istoric/home/<user>/<sesiune>/_STERS` sau `_MODIF`, păstrate implicit 30 de zile.
- **Compatibilitate exFAT/Windows**:
  - detectează și curăță automat caracterele interzise (`\ : * ? " < > |`), numele rezervate (`CON`, `PRN`, `COM1`...) și spațiile/punctele finale;
  - detectează coliziunile de tip case-insensitive (`Fisier.txt` vs `fisier.txt`) și le rezolvă automat cu `--force-case` sau te avertizează să le rezolvi manual.
- **Protecții de siguranță**:
  - refuză să ruleze ca root;
  - verifică faptul că destinația chiar este pe alt filesystem, nu pe discul intern (evită backup „în gol” pe un mountpoint nemontat);
  - testează scrierea pe destinație (detectează HDD montat read-only);
  - blochează rulările suprapuse cu un lock pe stick (`flock`);
  - refuză backup-ul dacă sursa pare goală în mod suspect sau dacă procentul de ștergeri depășește un prag configurabil (`--max-delete-percent`);
  - verifică spațiul liber înainte de a scrie ceva pe disc.
- **Mod simulare (`--dry-run`)**: arată exact ce s-ar întâmpla, fără nicio modificare.
- **Notificări desktop** (`notify-send`) la început și la final de backup.
- **Suport multi-laptop**: fiecare calculator își are propriul folder pe stick (după hostname), iar fiecare utilizator își are propriul istoric.

## Cerințe

- Linux, Python 3.
- `rsync` instalat (`sudo apt install rsync`).
- Opțional: `notify-send` pentru notificări desktop.

## Utilizare

```bash
./backup_exfat.py <sursa1> [sursa2 ...] <destinatie>
```

Ultimul argument este întotdeauna folderul de destinație (stick/HDD extern); toate celelalte sunt foldere sursă.

### Exemple

```bash
# Backup simplu, un folder
./backup_exfat.py ~/Documents /media/dan/stick

# Backup mai multe foldere deodată
./backup_exfat.py ~/Desktop ~/Documents /media/dan/stick

# Simulare, fără nicio modificare pe disc
./backup_exfat.py ~/Documents /media/dan/stick --dry-run

# Output detaliat (listă completă de fișiere transferate)
./backup_exfat.py ~/Documents /media/dan/stick --verbose

# Rezolvă automat coliziunile de nume case-insensitive
./backup_exfat.py ~/Documents /media/dan/stick --force-case
```

### Opțiuni

| Opțiune | Implicit | Descriere |
|---|---|---|
| `-n`, `--dry-run` | — | Simulare, fără modificări fizice |
| `-v`, `--verbose` | — | Output detaliat rsync (listing complet per fișier) |
| `--force-case` | — | Redenumește automat fișierele care se bat case-insensitive (exFAT) |
| `--allow-internal` | — | Permite backup pe discul intern (nu doar pe filesystem extern) |
| `--max-delete-percent N` | `50` | Refuză backup-ul dacă peste N% din fișierele de pe stick ar fi șterse (100 = dezactivează verificarea) |
| `--marja-mb N` | `200` | Marjă de siguranță la verificarea spațiului liber (MB) |
| `--zile-istoric N` | `30` | Câte zile se păstrează sesiunile din istoric înainte de a fi curățate automat |

## Structura pe stick

```
<stick>/<hostname>/<cale_absolută_sursă>/...              ← backup curent, oglindă a sursei
<stick>/<hostname>/_Istoric/home/<user>/<timestamp>/
                                          ├── _STERS/...   ← fișiere/foldere șterse de pe laptop
                                          ├── _MODIF/...   ← versiuni vechi ale fișierelor modificate
                                          └── redenumiri.log
```

Prefixul `<hostname>` separă backup-urile provenite de pe laptopuri diferite pe același stick; fiecare utilizator (`<user>`) își are propriul istoric, curățat independent.

## Cum funcționează un backup (pe scurt)

1. **Planificare** (nu modifică nimic): curăță/verifică numele incompatibile cu exFAT, indexează fișierele din sursă (cu hash), verifică pragul de siguranță la ștergeri, calculează spațiul necesar.
2. **Verificare spațiu agregat** pe toate sursele față de spațiul liber de pe destinație.
3. **Execuție**: detectează mutările/ștergerile față de starea anterioară de pe stick, apoi rulează `rsync` pentru restul modificărilor; fișierele înlocuite/șterse ajung în `_MODIF`/`_STERS`, nu se pierd.
4. **Curățare istoric**: șterge sesiunile mai vechi de `--zile-istoric` zile.
5. **Sumar final** cu numărul de fișiere noi/modificate/mutate/șterse, durată, spațiu.

## Recuperarea unui fișier șters/modificat

Fișierele nu sunt niciodată șterse definitiv de script — caută-le în:

```
<stick>/<hostname>/_Istoric/home/<user>/<data_sesiunii>/_STERS/...
<stick>/<hostname>/_Istoric/home/<user>/<data_sesiunii>/_MODIF/...
```

## Note

- Scriptul **nu** copiază linkuri simbolice (rsync rulează fără `-l`) — nu sunt suportate de exFAT.
- Pentru surse foarte mari (prima rulare, mii de fișiere), backup-ul poate dura; există un timeout intern de 1 oră per folder sursă.
- Dacă vezi eroarea „altă instanță rulează deja”, dar ești sigur că nu e adevărat, poți șterge manual lock-ul indicat în mesaj.
