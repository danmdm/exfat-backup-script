<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🚀 Smart Sync Backup Script (Linux -> exFAT)</title>
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-color: #f8fafc;
            --text-muted: #94a3b8;
            --accent-color: #38bdf8;
            --code-bg: #0f172a;
            --border-color: #334155;
            --warning-color: #f59e0b;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
            margin: 0;
            padding: 20px;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
            background: var(--card-bg);
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border-color);
        }

        h1 {
            color: #ffffff;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 12px;
            margin-top: 0;
            font-size: 1.8em;
        }

        h2 {
            color: #ffffff;
            margin-top: 30px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 8px;
            font-size: 1.3em;
        }

        h3 {
            color: var(--text-color);
            font-size: 1.1em;
            margin-top: 20px;
        }

        p, li {
            color: var(--text-color);
        }

        ul, ol {
            padding-left: 20px;
        }

        ul.features-list {
            list-style: none;
            padding-left: 0;
        }

        ul.features-list li {
            background-color: var(--code-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 12px;
        }

        ul.features-list strong {
            color: var(--accent-color);
        }

        code {
            background-color: var(--code-bg);
            color: var(--accent-color);
            padding: 3px 6px;
            border-radius: 4px;
            font-family: "Fira Code", Monaco, Consolas, "Courier New", monospace;
            font-size: 0.9em;
            border: 1px solid var(--border-color);
        }

        pre {
            background-color: var(--code-bg);
            padding: 16px;
            border-radius: 8px;
            overflow-x: auto;
            border: 1px solid var(--border-color);
        }

        pre code {
            background-color: transparent;
            padding: 0;
            border: none;
            color: #e2e8f0;
        }

        hr {
            border: none;
            border-top: 1px solid var(--border-color);
            margin: 30px 0;
        }

        .note {
            font-style: italic;
            color: var(--text-muted);
        }
    </style>
</head>
<body>

<div class="container">
    <h1>🚀 Smart Sync Backup Script (Linux -> exFAT)</h1>
    <p>Un script Python pentru backup incremental automatizat de pe un laptop cu sistem Linux pe medii de stocare externe (HDD/SSD formatate exFAT sau NTFS).</p>
    <p>Previne coruperea datelor, gestionează caracterele incompatibile cu exFAT, detectează mutările de fișiere prin hash și păstrează o versiune de siguranță a fișierelor modificate/șterse.</p>

    <hr>

    <h2>✨ Funcționalități Principale</h2>
    <ul class="features-list">
        <li>🧹 <strong>Autocurățare nume incompatibile (Pre-procesare):</strong> Detectează și redenumește direct pe laptop fișierele/folderele care conțin caractere interzise de exFAT (<code>*</code>, <code>:</code>, <code>?</code>, <code>"</code>, <code>&lt;</code>, <code>&gt;</code>, <code>|</code>), prevenind erorile de scriere.</li>
        <li>🛡️ <strong>Protecție la coliziuni de nume:</strong> În cazul numelor similare (ex: <code>bin*</code> și <code>bin?</code>), scriptul le redenumește unic (<code>bin_</code> și <code>bin_1</code>), prevenind comasarea accidentală a folderelor.</li>
        <li>⚡ <strong>Detecție inteligentă a mutărilor (Partial-Hash):</strong> Dacă redenumești sau muți un folder mare pe laptop, scriptul detectează modificarea prin hash rapid (MD5 bazat pe dimensiune + header/footer de 64KB) și mută fișierele corespunzător pe HDD, fără a le recopia de la zero.</li>
        <li>🔄 <strong>Sincronizare 1:1 cu rsync:</strong> Sincronizează doar fișierele modificate sau noi (folosind <code>--size-only</code> și potrivire de timp prin <code>os.utime</code>), afișând o bară dinamică de progres în timp real (<code>--info=progress2,stats2</code>).</li>
        <li>🔒 <strong>Detectare Read-Only &amp; Dispozitiv Conectat:</strong> Verifică dacă HDD-ul extern este montat corespunzător și dacă permite scrierea înainte de procesare, prevenind oprirea accidentală la jumătatea procesului.</li>
        <li>📦 <strong>Excludere automată fișiere temporare (Junk Filter):</strong> Omite fișierele temporare sau inutile (<code>.tmp</code>, <code>.DS_Store</code>, <code>__pycache__</code>, <code>thumbs.db</code>, lock-uri LibreOffice <code>.~lock.*</code>, <code>.Trash-*</code> etc.).</li>
        <li>🕒 <strong>Istoric de siguranță (30 de zile):</strong> Fișierele șterse sau modificate sunt salvate în folderul <code>_Istoric_Modificari/DATA_ORA/</code> timp de 30 de zile înainte de a fi curățate automat.</li>
        <li>📝 <strong>Jurnalizare (Log):</strong> Generare automată a fișierului <code>redenumiri.log</code> pe HDD la fiecare sesiune în care au fost modificate nume din cauza caracterelor speciale exFAT.</li>
        <li>💾 <strong>Verificare dinamică a spațiului liber:</strong> Calculează dimensiunea exactă a datelor noi sau modificate și oprește execuția de siguranță ÎNAINTE de transfer dacă spațiul liber de pe HDD este insuficient (include o marjă minimă de siguranță de 200 MB), prevenind erorile la jumătatea procesului.</li>
        <li>🔔 <strong>Notificări Desktop (Nativ Linux):</strong> Afișează notificări pe ecran (<code>notify-send</code>) la pornire, finalizare sau în caz de eroare (HDD deconectat, spațiu insuficient, disc Read-Only).</li>
        <li>🧪 <strong>Mod Simulare (--dry-run):</strong> Permite testarea completă a procesului fără a efectua nicio modificare pe disk (<code>python3 backup.py /sursa /destinatie --dry-run</code>).</li>
    </ul>

    <hr>

    <h2>🚀 Cerințe de Sistem</h2>
    <ul>
        <li><strong>Sistem de Operare</strong>: Linux (Ubuntu, Debian, Fedora, Arch, Linux Mint, etc.)</li>
        <li><strong>Utilitare Necesare</strong>: <code>python3</code>, <code>rsync</code>, <code>notify-send</code> (<code>libnotify-bin</code>)</li>
    </ul>

    <p>Pentru instalarea dependențelor pe sisteme bazate pe Debian/Ubuntu:</p>
    <pre><code>sudo apt update
sudo apt install python3 rsync libnotify-bin</code></pre>

    <hr>

    <h2>🛠️ Utilizare</h2>
    <p>Scriptul primește căile <strong>sursă</strong> ca primii parametri, iar <strong>ultimul parametru</strong> furnizat va fi întotdeauna calea către <strong>destinație</strong> (HDD-ul/stick-ul extern).</p>

    <h3>Sintaxă:</h3>
    <pre><code>./backup.py &lt;sursa1&gt; [sursa2 ...] &lt;destinatie&gt; [opțiuni]</code></pre>

    <h3>Exemple:</h3>

    <p><strong>1. Backup pentru un singur folder:</strong></p>
    <pre><code>./backup.py ~/Documents /media/dan/stick</code></pre>

    <p><strong>2. Backup pentru directoare multiple de pe laptop:</strong></p>
    <pre><code>./backup.py ~/Desktop ~/Documents ~/Downloads /media/dan/stick</code></pre>

    <p><strong>3. Rulare în mod Simulare (Dry-Run):</strong></p>
    <p>Afișează toate operațiunile (sanitizări, mutări, sincronizări rsync) fără a scrie sau șterge fizic pe disc.</p>
    <pre><code>./backup.py ~/Desktop ~/Documents ~/Downloads /media/dan/stick --dry-run</code></pre>
    <p class="note"><em>Notă:</em> Puteți folosi și scurtătura <code>-n</code>:</p>
    <pre><code>./backup.py ~/Documents /media/dan/stick -n</code></pre>

    <hr>

    <h2>📂 Structura Generată pe HDD</h2>
    <p>Destinația va avea următoarea structură curată:</p>
    <pre><code>/media/dan/stick/
├── Desktop/                       &lt;-- Sincronizare directă folder
├── Documents/                     &lt;-- Sincronizare directă folder
├── Downloads/                     &lt;-- Sincronizare directă folder
└── _Istoric_Modificari/
    └── 2026-03-09_18-30/          &lt;-- Folderul sesiunii curente
        ├── redenumiri.log         &lt;-- Jurnalul redenumirilor de pe laptop
        ├── _Fisiere_STERSE/        &lt;-- Fișierele șterse de pe laptop
        └── _Fisiere_MODIFICATE/    &lt;-- Versiunile vechi ale fișierelor modificate</code></pre>

    <hr>

    <h2>🔧 Permisiuni de Execuție</h2>
    <p>Pentru a rula scriptul direct, asigurați-vă că are drepturi de execuție:</p>
    <pre><code>chmod +x backup.py</code></pre>
</div>

</body>
</html>
