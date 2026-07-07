# Konzept der Modell-Pipeline — Transaction Classifier

Dieses Dokument beschreibt in natürlicher Sprache, **wie die Modell-Pipeline des
Transaction Classifiers aufgebaut ist**, welche Bausteine sie hat und **welche
Modelle bzw. Komponenten man dafür konkret braucht**. Es ist die konzeptionelle
Begleitung zum Notebook [`transaction_classifier.ipynb`](transaction_classifier.ipynb).

---

## 1. Was das System leisten soll

Die Aufgabe klingt simpel: Eine Banktransaktion kommt rein (Empfänger,
Verwendungszweck, Betrag), und heraus soll eine **Kategorie** kommen — z. B.
*REWE* → `supermarkt`, *ARAL* → `tanken`, ein Gehaltseingang → `gehalt`.

Der Knackpunkt ist aber nicht die einmalige Zuordnung, sondern zwei Anforderungen,
die den ganzen Aufbau prägen:

1. **Das System soll dazulernen** — jede manuelle Kategorisierung des Nutzers
   wird zu Trainingsmaterial. Der Klassifikator wird nicht einmal trainiert und
   dann eingefroren, sondern verbessert sich laufend mit der Nutzung.
2. **Neue Kategorien entstehen zur Laufzeit** — legt der Nutzer in der App eine
   neue Kategorie an (z. B. `haustier`), muss das Modell sie ohne Migration,
   ohne Sonderbehandlung und ohne kompletten Neuaufbau lernen können.

Dazu kommt der ehrliche Umgang mit Unsicherheit: Wenn das System sich nicht
sicher ist, soll es **nicht raten**, sondern den Nutzer fragen — und dabei
trotzdem seinen besten Tipp als Vorschlag mitliefern.

---

## 2. Die Pipeline in drei Stufen

Das Herzstück ist eine **Kaskade aus drei Stufen**. Eine Transaktion durchläuft
sie der Reihe nach; sobald eine Stufe ein sicheres Ergebnis liefert, ist Schluss.
Das ist bewusst so gebaut, weil Banktransaktionen extrem repetitiv sind — der
Großteil lässt sich schon ohne „echtes" Machine Learning erledigen.

### Stufe 1 — Merchant-Memory (Gedächtnis für bekannte Händler)

Die erste Stufe ist ein simples **Nachschlagewerk**: „Diesen Händler habe ich
schon einmal gesehen — welche Kategorie hat der Nutzer ihm damals gegeben?"

- Für jeden Händler wird ein **stabiler Schlüssel** gebildet (die ersten drei
  Tokens des bereinigten Namens). Dadurch landen `REWE Markt GmbH Filiale 4711`
  und `REWE Markt GmbH Köln` auf demselben Schlüssel — Filialvarianten kollabieren.
- Beim Nachschlagen wird ein **Präfix-Abgleich** gemacht: `aral` passt zu
  `aral station`, aber `deutsche bank` passt *nicht* zu `deutsche bahn`.
- Gespeichert wird pro Händler ein Zähler über die vergebenen Kategorien; die
  häufigste gewinnt.

Diese Stufe deckt in der Praxis **den Löwenanteil ab (~80 %)** — wiederkehrende
Mieten, Abos, der Stammsupermarkt, das Gehalt. Sie braucht kein trainiertes
Modell, nur ein Dictionary.

### Stufe 2 — ML-Modell (für neue, aber ähnliche Händler)

Was das Gedächtnis nicht kennt, geht an ein **echtes Klassifikationsmodell**.
Es soll generalisieren: Ein nie gesehener *PENNY* sieht im Verwendungszweck
ähnlich aus wie andere Supermärkte, ein *TotalEnergies* ähnelt ARAL und Shell.

Diese Stufe liefert nicht nur eine Kategorie, sondern eine **Wahrscheinlichkeit
pro Kategorie** — die brauchen wir für Stufe 3, um „sicher genug" von
„lieber nachfragen" zu unterscheiden. Details zu den benötigten Modellen in
Abschnitt 4.

### Stufe 3 — Fallback (ehrliche Unsicherheit)

Liegt die höchste Wahrscheinlichkeit aus Stufe 2 **unter einer Konfidenzschwelle**
(Default 0.55), gibt das System **keine feste Kategorie zurück**, sondern `None`
plus einen **Vorschlag** (den besten Tipp). In der App heißt das: „Bitte
kategorisieren — meintest du vielleicht `supermarkt`?" Der Nutzer entscheidet,
und seine Entscheidung fließt als Feedback zurück.

Die Schwelle ist der zentrale **Regler zwischen „lieber fragen" und „lieber
automatisch"** und sollte in den App-Einstellungen justierbar sein.

---

## 3. Die unterstützenden Bausteine (kein ML, aber essenziell)

Damit die Pipeline funktioniert, braucht sie neben den Modellen ein paar
„unspektakuläre" Komponenten, die aber über Erfolg oder Misserfolg entscheiden.

### Text-Normalisierung

Rohe SEPA-Verwendungszwecke sind voller **Rauschen**, das dem Modell nichts
bringt oder es sogar dazu verleitet, auswendig zu lernen statt zu generalisieren.
Vor allem entfernt bzw. vereinheitlicht die Normalisierung:

- **IBANs** (kontospezifisch, null Generalisierungswert),
- **SEPA-Referenzfelder** (`EREF+`, `MREF+`, `SVWZ+`, `KREF+` …),
- **Datumsangaben und lange Zahlen** (Kunden-, Filial-, Automatennummern),
- **Buchungstyp-Wörter** (`LASTSCHRIFT`, `KARTENZAHLUNG` … — stehen bei *jeder*
  Transaktion und tragen keine Kategorie-Information),
- **Umlaute und Groß/Kleinschreibung** (`BÄCKEREI` und `Baeckerei` werden gleich).

Ohne diesen Schritt würde das Modell an technischem Ballast hängenbleiben.

### Die Typ-Maske (harte Nebenbedingung über das Vorzeichen)

Das Vorzeichen des Betrags bestimmt den Typ: **negativ = Ausgabe, positiv =
Einnahme**. Jede Kategorie ist genau einem Typ zugeordnet (`gehalt` = Einnahme,
`supermarkt` = Ausgabe …). Vor der finalen Entscheidung werden alle Kategorien
mit **falschem Typ auf Wahrscheinlichkeit 0 gesetzt** und der Rest neu normiert.

Effekt: Eine Ausgabe kann **niemals** als `gehalt` klassifiziert werden, eine
Einnahme nie als `supermarkt` — selbst wenn der Text mehrdeutig wäre. Eine
billige, aber sehr wirksame Absicherung.

### Feedback-Schleife & Lazy Retraining

Jede Nutzeraktion ist Feedback: (a) ein Vorschlag wird bestätigt, (b) eine
automatische Zuordnung wird korrigiert, (c) eine `None`-Transaktion wird von Hand
kategorisiert. Alle drei füttern das System — **Korrekturen (b) sind die
wertvollsten Signale**.

Neu trainiert wird aber nicht bei jedem Feedback sofort, sondern **verzögert**
(ein „dirty"-Flag markiert das Modell als veraltet, der Retrain passiert erst
bei der nächsten Vorhersage). So kostet das Kategorisieren eines ganzen
CSV-Imports nur *einen* Retrain statt hunderter.

### Persistenz

Gespeichert werden **nur die Trainingsbeispiele als JSON**, nicht das fertig
trainierte Modell. Zwei Gründe: (1) Kein Versions-Ärger — gepickelte
sklearn-Objekte brechen bei Bibliotheks-Updates, rohe Beispiele + Retrain beim
Laden sind dagegen immun. (2) Die Beispiele sind eine simple Tabelle
(`text`, `merchant_key`, `typ`, `kategorie`) und passen direkt in eine
App-Datenbank (SQLite o. Ä.).

---

## 4. Was man an Modellen konkret braucht

Hier die Antwort auf „welche Modelle brauche ich" — aufgeteilt nach Rolle.

### Der Klassifikator-Kopf: Logistische Regression

In allen Varianten sitzt am Ende dieselbe **logistische Regression**. Sie ist
bewusst gewählt:

- Sie liefert **kalibrierte Wahrscheinlichkeiten** (`predict_proba`) — genau das,
  was Stufe 3 für die Konfidenzschwelle braucht.
- Mit `class_weight="balanced"` geht eine **neue Kategorie mit nur wenigen
  Beispielen** nicht gegen etablierte wie `supermarkt` unter — entscheidend für
  den „neue Kategorie zur Laufzeit"-Usecase.
- Sie ist klein, schnell und exportierbar (im Grunde nur eine Gewichtsmatrix +
  Bias-Vektor).

**Mindestdatenmenge:** Unter 4 Beispielen oder nur einer einzigen Klasse wird
gar nicht trainiert — dann arbeitet allein das Merchant-Memory.

### Die Feature-Extraktion: drei wählbare Modi

Damit die logistische Regression mit Text umgehen kann, muss der Text in Zahlen
(Vektoren) übersetzt werden. Dafür gibt es **drei austauschbare Varianten**
(Parameter `vectorizer`):

| Modus | Was es ist | Stärke | Kosten |
|---|---|---|---|
| `"tfidf"` | **TF-IDF auf Zeichen-n-Grammen** (2–5, `char_wb`) | robust, lernt nur aus den eigenen Daten, kommt mit zusammengeklebten Strings wie `NETFLIX.COMMREF` klar | keine, rein lokal |
| `"embedding"` | **Sentence-Embeddings**, eingefrorenes Modell `paraphrase-multilingual-MiniLM-L12-v2` | bringt allgemeines Sprachwissen mit, erkennt Ähnlichkeit auch ohne exakte Zeichenüberlappung | einmaliger Download (~470 MB), danach offline |
| `"ensemble"` | **beides kombiniert**, gewichtet gemischt (`weight_embedding`) | Kompromiss aus beidem | wie Embedding |

**Wichtig:** Das Embedding-Modell ist **vortrainiert und wird nicht mitverändert**
(eingefroren, `fit()` tut nichts). Es bringt generisches Sprachverständnis mit,
aber **kein** Retail-/Merchant-Wissen — das entsteht erst durch die logistische
Regression on top. Es läuft nach dem einmaligen Download vollständig lokal/offline,
was zum Offline-first-Ansatz des Projekts passt.

**Empirischer Befund aus dem Notebook:** TF-IDF ist der robuste Standard.
Embeddings helfen bei generalisierenden Fällen deutlich (im PENNY-Beispiel
Konfidenz 0.87 statt 0.37), das Ensemble liegt dazwischen. Welcher Modus und
welches Gewicht optimal sind, sollte man auf **echten Bankdaten empirisch
kalibrieren** statt blind zu wählen.

### Zusammengefasst — die Einkaufsliste

- **Ein Dictionary / Zähler-Struktur** für das Merchant-Memory (kein ML).
- **Eine logistische Regression** als Klassifikator-Kopf (Stufe 2).
- **Mindestens ein Feature-Extraktor:**
  - TF-IDF (immer verfügbar, keine Abhängigkeit über sklearn hinaus), **und/oder**
  - ein Sentence-Embedding-Modell (`sentence-transformers`,
    `paraphrase-multilingual-MiniLM-L12-v2`, ~470 MB).
- **Bibliotheken:** `scikit-learn` (Pipeline, TF-IDF, logistische Regression),
  `numpy`; optional `sentence-transformers` nur für die Embedding-/Ensemble-Modi.

Für einen reinen TF-IDF-Betrieb braucht man also **nur scikit-learn** — kein
großer Modell-Download, alles lokal.

---

## 5. Wie sich das System über die Zeit verhält

Am Anfang (wenige Beispiele) ist das System **zu Recht vorsichtig**: Stufe 2
bleibt oft unter der Schwelle und liefert nur Vorschläge, während das Memory
schon zuverlässig die wiederkehrenden Fälle abdeckt. Mit jedem Monat
Kontoauszug steigen die Konfidenzen, und immer mehr läuft automatisch —
im Notebook messbar (PENNY: 0.40 → 0.57 → 0.66 → 0.74 über 1/3/6/12 Monate).

Das ist genau das gewünschte Verhalten: **erst fragen, mit wachsendem Vertrauen
zunehmend automatisch.**

---

## 6. Hinweise für die App-Integration

- **Feedback konsequent anschließen:** Bestätigung, Korrektur und manuelle
  Kategorisierung sind alle Feedback — besonders Korrekturen sind Gold wert.
- **Unterkategorien** sind reine Anzeige-Logik der App. Das Modell lernt auf den
  Blatt-Slugs (`supermarkt`, nicht `lebensmittel`) und muss von der Hierarchie
  nichts wissen.
- **Nicht-Python-Umgebungen** (das Projekt zielt auf macOS + GrapheneOS,
  offline-first): Die Architektur ist 1:1 übertragbar. Das Memory ist ein
  Dictionary; TF-IDF + logistische Regression gibt es auch in JS/TS — oder man
  trainiert in Python und exportiert nur die Gewichte (Matrix + Bias), die
  Inferenz ist dann ein Matrix-Vektor-Produkt. Erfahrungsgemäß deckt das Memory
  allein bereits den Großteil ab.
- **Nächster sinnvoller Schritt:** den Classifier auf einen echten CSV-Export
  einer Bank loslassen und die Rausch-Muster (`_NOISE_PATTERNS`) an deren
  Verwendungszweck-Format anpassen.
