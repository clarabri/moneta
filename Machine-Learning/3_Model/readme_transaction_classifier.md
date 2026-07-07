Man sieht das gewünschte Verhalten: Am Anfang ist das System vorsichtig und
macht nur Vorschläge; mit mehr bestätigten Daten überschreitet die Konfidenz
die Schwelle und die Kategorisierung läuft automatisch. Die Schwelle
(`confidence_threshold`) ist dein Regler zwischen „lieber fragen" und
„lieber automatisch" — ein guter UX-Default ist, sie in den App-Einstellungen
justierbar zu machen.

## 9. Integration in deine App — Hinweise

**Feedback-Loop richtig anschließen.** Jede der drei UI-Aktionen ist Feedback:
(a) User bestätigt einen Vorschlag, (b) User korrigiert eine automatische
Zuordnung, (c) User kategorisiert eine `None`-Transaktion. Alle drei →
`add_feedback()`. Besonders (b) ist wichtig: Korrekturen sind die wertvollsten
Trainingssignale.

**Unterkategorien.** Das Modell lernt auf den Blatt-Slugs (`supermarkt`, nicht
`lebensmittel`). Die Eltern-Zuordnung ist reine Anzeige-Logik deiner App —
das Modell muss davon nichts wissen.

**Wenn die App nicht in Python läuft** (dein Entwurf zielt ja auf
macOS + GrapheneOS, offline-first): Die Architektur ist 1:1 übertragbar.
Das Merchant-Memory ist ein Dictionary, TF-IDF + Logistische Regression gibt
es auch als reine JS/TS-Implementierungen — oder du trainierst in Python und
exportierst nur die Gewichte (eine Matrix + Bias-Vektor, die Inferenz ist ein
Matrix-Vektor-Produkt). Erfahrungsgemäß deckt das Memory allein schon den
Großteil ab, weil Transaktionen so repetitiv sind.

**Nächster sinnvoller Schritt:** den Classifier auf einen echten CSV-Export
deiner Bank loslassen. Die `_NOISE_PATTERNS` sind auf typische SEPA-Formate
ausgelegt, aber jede Bank hat Eigenheiten im Verwendungszweck-Format.