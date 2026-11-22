# PHYSICS_CONTRACT.md — Verbindliche Spezifikation für `physik-sims`

Jede Simulation in `sims/` ist ein eigenständiges, taktiles Physik- oder Mathematik-Werkzeug („Fidget-Toy“ und Unterrichtslabor). Alle Simulationen **müssen** diese Spezifikation einhalten. `build.py --check` prüft zentrale Teile davon automatisiert vor jedem Deploy.

---

## 1. Architektur & Single-File-Prinzip

1. **Vollständige Autarkie:** Jede Datei in `sims/**/*.html` enthält sämtliches HTML, CSS und JavaScript inline (`<style>` und `<script>`).
2. **Null externe Abhängigkeiten:** Keine externen CDNs, Google Fonts, Bilder, `<script src="http...">`, `<link href="http...">` oder `fetch()`-Aufrufe. Jede Datei muss offline (z. B. nach „Sichern“ oder per *Teilen → In Safari öffnen* nach AirDrop) identisch funktionieren wie über GitHub Pages.
3. **Stabile Slugs:** Dateinamen unter `sims/` sind sprechende Kleinbuchstaben-Slugs mit Bindestrich (z. B. `sims/physik/fadenpendel.html`). Einmal veröffentlichte Pfade dürfen nicht umbenannt werden, da gedruckte QR-Codes auf Arbeitsblättern dauerhaft darauf verweisen.

---

## 2. Standardisierter Metadaten-Header

Jede Simulationsdatei **muss** ganz oben (direkt vor oder nach `<!DOCTYPE html>`, empfohlen in den ersten 40 Zeilen) einen standardisierten HTML-Kommentarblock enthalten:

```html
<!--
@id: fadenpendel
@title: Gedämpftes Fadenpendel
@subject: physik
@topic: Mechanik & Schwingungen
@grade: Sek I / Sek II
@tags: Pendel, Schwingung, Energieerhaltung, Dämpfung, Phasenraum
@summary: Taktiles Fadenpendel mit RK4-Integration, Vektor-Overlays, Live-Energiebilanz und Phasenraum-Diagramm.
@controls: Masse direkt ziehen & loslassen | Slider: Seillänge L, Erdbeschleunigung g, Dämpfung γ | Ebenen: Vektoren, Energiebalken, Phasenraum
@representations: Kraft- & Geschwindigkeitsvektoren, Live-Energiebalken, Phasenraum (φ, ω)
@presets: ungedaempft, stark-gedaempft, mond, jupiter
-->
```

**Pflichtfelder:** `@id`, `@title`, `@subject` (`physik` | `mathe`), `@topic`, `@grade`, `@tags`, `@summary`, `@controls`, `@representations`.
**Optional:** `@presets` (kommagetrennte Liste unterstützter `?preset=...`-URL-Parameter für Arbeitsblätter).

---

## 3. Numerische Stabilität & Physik-Standards

1. **Integrationsverfahren:**
   * Für Schwingungen, Felder, Pendel und Bahnkurven **niemals** naives (explizites) Euler-Verfahren verwenden.
   * Pflicht: **RK4 (Runge-Kutta 4. Ordnung)** oder **Velocity Verlet** (symplektisch, ideal für konservative Systeme / N-Körper).
2. **Sub-Stepping & Frame-Delta-Clamping:**
   * `frameDt` aus `requestAnimationFrame` immer hart begrenzen: `const frameDt = Math.min((now - lastTime) / 1000, 0.05);` (verhindert Sprünge nach Tab-Wechsel oder Geräte-Standby).
   * Integration mit festem internen Zeitschritt `FIXED_DT <= 0.002` s (`dt <= 2 ms`) über einen Zeit-Akkumulator (`while (acc >= FIXED_DT) { step(FIXED_DT); acc -= FIXED_DT; }`).
3. **Singularitäten abfangen:**
   * Bei $1/r^2$- oder $1/r$-Kräften (Gravitation, Coulomb) **immer** einen Softening-Parameter $\varepsilon > 0$ einsetzen: $r_{\text{eff}}^2 = r^2 + \varepsilon^2$.
   * Division durch Null, $\arcsin/\arccos$-Rundungsfehler außerhalb $[-1, 1]$ und extreme Geschwindigkeiten sauber abfangen.
4. **SI-Einheiten & physikalische Korrektheit:**
   * Rechnen in echten SI-Einheiten (m, s, kg, N, J, rad/s) — erst beim Zeichnen auf Canvas-Pixel skalieren.
   * Im HUD und auf Achsen konsistente SI-Einheiten angeben (z. B. `L = 1,20 m`, `E = 0,48 J`).

---

## 4. iPadOS-, Touch- & Canvas-Ergonomie

1. **Viewport & Safe Areas:**
   * `<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">`
   * Container-Höhe über `100dvh` (Dynamic Viewport Height), damit die Safari-Leiste auf dem iPad nichts verdeckt.
2. **Pointer Events statt Mouse/Touch-Duplikaten:**
   * Ausschließlich `pointerdown`, `pointermove`, `pointerup`, `pointercancel` verwenden.
   * Auf dem `<canvas>` zwingend: `touch-action: none; user-select: none; -webkit-user-select: none; -webkit-touch-callout: none;`.
   * Beim Greifen eines Objekts `canvas.setPointerCapture(e.pointerId)` nutzen und die aktive `pointerId` verfolgen (verhindert Abbruch beim schnellen Ziehen oder versehentliches Handballen-Auslösen).
3. **Großzügige Hitboxen:**
   * Interaktive Canvas-Objekte (Massen, Ladungen, Knoten) haben mindestens **36 px** (besser 44 px) effektiven Touch-Radius (`hitRadius >= 22` px Radius bzw. >= 44 px Durchmesser), unabhängig von ihrer gezeichneten Größe.
   * Buttons und Slider-Targets haben mindestens `36 px` Höhe.
4. **Retina-Skalierung:**
   * `const dpr = Math.min(window.devicePixelRatio || 1, 2);`
   * Canvas-Backing-Store (`canvas.width = rect.width * dpr`) per `ResizeObserver` aktualisieren und `ctx.setTransform(dpr, 0, 0, dpr, 0, 0)` setzen.

---

## 5. Didaktik, Ästhetik & AB-Integration

1. **Sofort interaktiv („Fidget-First“):**
   * Keine Startbildschirme oder Modals. Die Simulation läuft oder reagiert ab dem ersten Pixel-Kontakt.
   * Direktes Greifen/Ziehen im Canvas hat Vorrang vor Menüs.
2. **Ruhiges Labor-Design:**
   * Inspiriert von 3Blue1Brown / Desmos (standardmäßig klares Dark-Lab- oder Light-Lab-Theme mit hohem Kontrast für Beamer & iPad).
   * Full-Viewport-Canvas + kompaktes, einklappbares HUD (für reinen Fidget-/Beamer-Modus ausblendbar).
   * **Maximal 3–4 klare Slider** + `Play/Pause` + `Reset` (ggf. `Spur löschen`).
3. **Mindestens eine umschaltbare Repräsentationsebene:**
   * Jede Simulation bietet mindestens eine ein-/ausblendbare analytische Ebene (z. B. Kraft-/Geschwindigkeitsvektoren, Live-Energiebalken, Phasenraum, Feldlinien, Funktionsgraph).
4. **URL-Presets für Arbeitsblätter:**
   * Simulationen lesen optionale Query-Parameter (`?preset=...` sowie zentrale Parameter wie `?L=1.5&g=1.62&gamma=0.15`), sodass QR-Codes auf Arbeitsblättern direkt ein passendes Experiment-Szenario starten können.
5. **Arbeitsblatt-Kompatibilität (`Schule`-Pipeline):**
   * `build.py` exportiert `catalog.json` inklusive stabiler GitHub-Pages-URL, `@controls` und `@presets`.
   * Jeder QR-Code auf einem Arbeitsblatt sollte von einem kurzen Hinweis begleitet werden, *was* die Lernenden ziehen/verstellen und *welche* Repräsentationsebene sie zuschalten sollen.
