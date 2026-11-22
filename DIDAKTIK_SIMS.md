# DIDAKTIK_SIMS.md — Didaktisches Leitbild & Kriterien für Simulationen

> **Zweck & Geltungsbereich:** Verbindliche didaktische Qualitätskriterien für interaktive Physik- und Mathematik-Simulationen in `physik-sims` (Sek I & Sek II).  
> **Abgrenzung:** Technische Vorgaben (Numerik, Pointer Events, Single-File-Build) stehen in [`PHYSICS_CONTRACT.md`](PHYSICS_CONTRACT.md). Dieses Dokument regelt **Didaktik, Cognitive Load und visuelle Reduktion**.

---

## 1. Wann ist eine Simulation sinnvoll — und wann nicht?

Eine Simulation ist kein Selbstzweck und ersetzt kein echtes Experiment, wenn der reale Handgriff besser trägt.

### Sinnvoller Einsatz (Mehrwert gegenüber dem Realexperiment)
1. **Unsichtbares modellieren:** Submikroskopische oder abstrakte Ebenen sichtbar machen (Teilchenbewegung, Eisgitter, elektrische/magnetische Felder, Elektronenfluss).
2. **Zeit & Raum skalieren:** Extrem schnelle Vorgänge per `Pause` und Einzelschritt (`|>`) einfrieren oder langsame Vorgänge (Planetenbahnen, Zerfall) raffen.
3. **Idealfälle & Grenzen testen:** Bedingungen isolieren, die real kaum sauber herstellbar sind (reibungslos, Vakuum, absoluter Nullpunkt `0 K`, Mond-/Jupiter-Gravitation).
4. **Systematische Variablenkontrolle:** Zwei Zustände oder Stoffe unter exakt gleichen Randbedingungen unmittelbar nacheinander vergleichen.

### Kein Ersatz für das Realexperiment
* Wenn das Phänomen in 2 Minuten sicher, haptisch und mit echter Messunsicherheit auf dem Tisch erfahrbar ist (z. B. Thermometer ablesen, Federkraftmesser ziehen, Bimetall erwärmen), hat das Realexperiment Vorrang. Die Simulation dient dann höchstens als **Deutungsmodell** (z. B. *„Was passiert dabei im Unsichtbaren?“*).

---

## 2. Cognitive Load & Radikale Reduktion

Lernende – besonders in der Sek I – bringen begrenztes Arbeitsgedächtnis mit. Jedes zusätzliche Bedienelement, jede Textzeile und jedes zweite Fenster erzeugt **Extraneous Cognitive Load** und lenkt vom physikalischen Kern ab.

### A. Ein visueller Fokus statt „Cockpit“
* **Eine Hauptbühne:** Lieber ein zentrales, klares Gefäß/Objekt als zwei konkurrierende Kästen nebeneinander (Split-Attention vermeiden).
* **Räumliche Kontiguität:** Messgeräte und Werkzeuge gehören **direkt an den Wirkort** – das Thermometer steckt *im* Gefäß, Brenner/Eisbad stehen *direkt unter* dem Gefäßboden, ein Kraftpfeil sitzt *am* Körper.
* **Keine Dauer-Textleisten:** Keine permanenten Banner über konstante Parameter oder Arbeitsanweisungen in der Simulation. Die Geschlossenheit eines Gefäßes sieht man am Deckel; die Forschungsfrage steht auf dem Arbeitsblatt.

### B. Ikonische Sprache & taktile Ästhetik statt Textwänden
* **Dual Coding:** Symbole schlagen Text. Neben Stoffnamen gehören kleine Teilchen-Icons (Einzelkugel vs. zweiatomiges Molekül vs. V-förmiges $\mathrm{H_2O}$), Zustands-Buttons nutzen klare Piktogramme (`Fest`, `Flüssig`, `Gas`), Skalen sind unmittelbar ablesbar.
* **Taktile, wertige Gestaltung (ohne Sterilität):** Reduziert im *Inhalt*, aber liebevoll und handwerklich sauber im *Design* – echte Glasreflexe, warme Glühlampen, klickbare Schalter und griffige Regler wecken Neugier, solange keine dekorativen Elemente vom physikalischen Wirkzusammenhang ablenken.
* **Selbsterklärende Steuerung:** Eine gute Simulation lässt sich ohne Anleitungssatz sofort bedienen („Fidget-First“).
* **Sparsamste Standardansicht:** Beim Öffnen laufen keine analytischen Overlays. `Pause`, Einzelschritt (`|>`) und `Reset` reichen als Grundbesteck.

### C. Gezielte Steuerung für den Erkenntnisgewinn
* **Variablenklarheit:** Jede Simulation macht sofort greifbar, *was* verändert wird (unabhängige Variable) und *was* man beobachtet.
* **Stufenlos + Vergleichspunkte:** Sowohl kontinuierliches Verändern (z. B. direktes Heizen/Kühlen am Objekt) als auch schnelle Vergleichspunkte (z. B. Zustands-Buttons oder `°C`-/`K`-Umschalter direkt am Thermometer) verhindern fummeliges Suchen.
* **Fachliche Sauberkeit beim Stoffvergleich:** Keine grundverschiedenen Stoffklassen (Metallgitter, Molekülflüssigkeit, Edelgas) kommentarlos durch identische Kugeln gleichsetzen.

---

## 3. Erkenntnisgewinn & Fehlkonzept-Schutz (Germane Load)

1. **Implizit sichtbar statt Spoiler-Textbox:**
   * Besondere Effekte (z. B. das offene Eis-Wabengitter und der leicht steigende Raumbedarf beim Gefrieren von Wasser) sollen **beobachtbar** sein, ohne dass ein Hinweistext die Erkenntnis vorwegnimmt (*„Achtung: +9 % Volumen!“*).
   * *Vorteil:* Dieselbe Simulation bleibt schlank und lässt sich für verschiedene Fragestellungen wiederverwenden (erst Aggregatzustände, später Dichteanomalie oder Temperaturskalen bis `0 K`).
2. **Rauscharme Repräsentationen:**
   * Keine 40 gleichzeitig flackernden Pfeile oder geskriptete Scheinkurven ohne echte Physik dahinter.
   * Wo Bewegung sichtbar gemacht werden soll, reicht oft **ein** farbig markiertes Spur-Teilchen oder ein einzelner sauberer Vektor.
3. **Empirische Fehlkonzepte strukturell ausschließen:**
   * Teilchen behalten unabhängig von der Temperatur exakt dieselbe Eigengröße und Gesamtanzahl im geschlossenen System.
   * Der Hintergrund im Teilchenraum ist eindeutig Leerraum (kein „blaues Wasser“, in dem Kugeln schwimmen).

---

## 4. Stufen-Taktgefühl (Sek I vs. Sek II)

| Dimension | Sekundarstufe I (Kl. 5–10) | Sekundarstufe II (EF–Q2) |
| :--- | :--- | :--- |
| **Optik & Kontext** | Anschauliches Labor (Becherglas, Thermometer, Brenner/Eisbad), helle oder klar gerahmte Bühne | Ruhiges, kontrastreiches Labor- oder Koordinaten-Design |
| **Einheiten & Skalen** | `°C` als Standard, am Thermometer umschaltbar auf `K` (absoluter Nullpunkt) | Volle SI-Einheiten (`K`, `rad/s`, `J`, `N`) |
| **Stoff- & Modellauswahl** | Alltagsnahe Beispiele (`Wasser`, `Ethanol`/Normalstoff) mit klaren Teilchen-Icons | Abstraktere Modelle und Parameterbereiche |
| **Zusatz-Ebenen** | Maximal 1–2 anschauliche Hilfen (z. B. Spur eines Teilchens) | Analytische Ebenen (Phasenraum, Energiebalken, Vektoren) zuschaltbar |

---

## 5. Zusammenspiel mit dem Arbeitsblatt (`Schule`-Pipeline)

1. **Klare Aufgabenteilung:** Die Simulation bleibt minimalistisch und textarm; das **Arbeitsblatt** liefert den Kontext, benennt die **unabhängige Variable** und die **konstanten Größen** und stellt die Leitfrage.
2. **POE-Zyklus (Predict – Observe – Explain):** Aufträge regen Lernende an, *zuerst* eine Vermutung zu notieren, *dann* gezielt in der Simulation (gern mit `Pause` / `|>`) zu beobachten und anschließend zu erklären.
3. **Wiederverwendbare URL-Presets:** Über `?preset=...` startet die Simulation direkt in der passenden Ausgangslage für die jeweilige Teilaufgabe.

---

## 6. 5-Punkte-Gate vor jeder neuen Simulation

Vor der Implementierung einer neuen Simulation wird kurz geprüft:
1. **Legitimation:** Was leistet diese Simulation, was ein Realexperiment auf dem Tisch nicht kann?
2. **Text- & Element-Diät:** Lässt sich die Simulation ohne einen einzigen Erklärsatz bedienen – und steckt jedes Werkzeug direkt am Objekt?
3. **Variablenkontrolle:** Lassen sich gezielte Vergleiche (z. B. gleiche Temperatur, verschiedener Stoff) ohne Fummeln durchführen?
4. **Kein Spoiler, kein Rauschen:** Entdecken Lernende selbst, statt Textboxen abzulesen? Gibt es keine überladenen Pfeil-/Kurven-Overlays?
5. **Stufenpassung & Wiederverwendbarkeit:** Passt die Darstellung zur Zielstufe (Sek I / Sek II) und trägt sie ggf. auch eine zweite Fragestellung (z. B. über `?preset=...` oder einen Einheiten-Schalter)?

---

## 7. Wissenschaftliche Fundierung (Quellen in `quellen/` & `LITERATUR_INDEX.md`)

Die Kriterien dieses Leitbilds stützen sich auf folgende fachdidaktische Arbeiten (vollständig verzeichnet im [Physik-Literatur-Index](../Schule/materialien/physik/LITERATUR_INDEX.md#5-simulationen-modellbildung-digitale-experimente)):

* **Simulation + Realexperiment kombinieren (*Wörner, Scheiter & Kuhn*):** Simulationsexperimente (SE) ergänzen Realexperimente (RE) als Brücke zwischen sichtbarem Phänomen und theoretischem Modell (z. B. Strahlenoptik Kl. 7/8); QR-Codes auf Arbeitsblättern senken die Einstiegshürde auf Tablets.
* **Epistemisches Werkzeug statt Demo (*Caner, 2026*):** Entlang des **5E-Modells** (*Explore*, *Explain*, *Elaborate*) entfalten Simulationen ihre Wirkung nicht als passive Lehrerdemonstration, sondern wenn Lernende kausal-mechanistische Zusammenhänge selbst prüfen und Darstellungen koordinieren.
* **3. Säule der Erkenntnisgewinnung & NOS (*Heysel & Bertoldi, 2025*):** Besonders in der Sek II sind Simulationen neben Experiment und Theorie Teil von *Nature of Science* (Modellannahmen, Schrittweiten, Grenzen der Simulation explizit reflektieren).
* **Rückübertragung auf die Realität (*Holec & Spodniakova Pfefferova*):** Nach der Variation von Anfangsbedingungen (*„What happens if…?“*) folgt im Unterricht zwingend der Abgleich mit realen Störgrößen und Rahmenbedingungen.
* **Wiederholtes Manipulieren & Motivation (*Banda & Nzabahimana, 2023; Álvarez-Siordia et al., 2025; Aguay-Saquicaray et al., 2025*):** Eigenständiges Wiederholen und Ausprobieren stärkt Konzeptverständnis, Selbstwirksamkeit und Problemlösen – vorausgesetzt, die Oberfläche überfordert nicht durch Bedienkomplexität.

