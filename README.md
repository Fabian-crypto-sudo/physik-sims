# physik-sims

Leichtgewichtige, taktile Physik- und Mathematik-Simulationen für Unterricht, Beamer, iPad und Arbeitsblätter.

**Live-Übersicht (GitHub Pages):**  
`https://fabian-crypto-sudo.github.io/physik-sims/`

## Struktur

- `sims/` — Eigenständige Single-File-HTML-Simulationen (inline CSS/JS, keine externen Abhängigkeiten), sortiert nach Fach (`sims/physik/`, `sims/mathe/`).
- `DIDAKTIK_SIMS.md` — Didaktisches Leitbild zu Legitimation, Cognitive Load, radikaler Reduktion und Sek-I-/Sek-II-Design.
- `PHYSICS_CONTRACT.md` — Verbindliche technische Vorgaben zu Numerik (RK4 / Velocity Verlet, Sub-Stepping, Softening) und iPad-Touch-Ergonomie.
- `build.py` — Reines Python-Skript (nur Standardbibliothek), das `sims/**/*.html` validiert und `index.html` (inkl. Live-Suche, Filter & SVG-QR-Codes) sowie `catalog.json` erzeugt.
- `.github/workflows/deploy.yml` — Baut und deployt automatisch auf GitHub Pages bei jedem Push auf `main`.

## Lokal bauen & prüfen

```bash
python3 build.py --check
```

## Integration mit Arbeitsblättern (`Schule`)

Jede Simulation ist über ihre stabile GitHub-Pages-URL direkt verlinkbar und als QR-Code in `Schule`-Arbeitsblättern nutzbar (z. B. über `::: experiment` mit `qr="..."` und `qr_label="..."`):

```markdown
::: experiment {titel="Schwingung untersuchen" qr="https://fabian-crypto-sudo.github.io/physik-sims/sims/physik/fadenpendel.html?preset=ungedaempft" qr_label="Simulation: Fadenpendel"}
...
:::
```

Alle verfügbaren URLs, Bedienhinweise (`controls`), Repräsentationsebenen und `?preset=...`-Varianten stehen automatisch in `catalog.json`.
