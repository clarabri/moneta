# Konzept: Automatische Kategorisierung von Kontoauszugsdaten mit einem lokalen Sprachmodell

## Ziel und Rahmenbedingungen

Ziel ist die automatische Zuordnung von Banktransaktionen zu einem persönlichen, zweistufigen Kategoriensystem (acht Hauptkategorien wie „groceries", „mobility" oder „fixed costs", darunter rund 35 Unterkategorien). Die Verarbeitung soll vollständig lokal auf dem eigenen Rechner stattfinden — es werden keine Finanzdaten an externe Dienste übertragen. Das Modell soll so klein wie möglich sein, damit Training und Inferenz auch ohne dedizierte GPU praktikabel bleiben.

## Grundidee

Verwendungszwecke und Empfängernamen auf Kontoauszügen sind kurze, formelhafte Texte („REWE SAGT DANKE", „DB Vertrieb GmbH", „Stadtwerke München Abschlag"). Für die Zuordnung solcher Texte zu einer festen Menge von Kategorien ist kein generatives Sprachmodell nötig. Stattdessen wird ein deutschsprachiges Encoder-Modell (DistilBERT, ca. 67 Millionen Parameter) mit einem Klassifikationskopf versehen und auf den eigenen Daten feinjustiert. Das Modell liest den Transaktionstext und gibt für jede Kategorie eine Wahrscheinlichkeit aus; die wahrscheinlichste Kategorie wird als Vorschlag übernommen.

Trainiert wird flach auf den Unterkategorien. Die Hauptkategorie ergibt sich anschließend automatisch aus der Zuordnungstabelle, da jede Unterkategorie genau einer Hauptkategorie angehört. Kategorien ohne Unterteilung (etwa „family") werden direkt als eigenes Label geführt.

## Einbettung in die Gesamtpipeline

Der Klassifikator ist die mittlere Stufe einer dreistufigen Pipeline:

Zuerst prüft ein Händlergedächtnis (Merchant Memory), ob der Empfänger bereits bekannt ist und in der Vergangenheit eindeutig einer Kategorie zugeordnet wurde. Ist das der Fall, wird diese Zuordnung ohne Modellaufruf übernommen — das deckt erfahrungsgemäß den Großteil wiederkehrender Buchungen ab.

Nur unbekannte oder mehrdeutige Transaktionen erreichen die zweite Stufe, den feinjustierten Klassifikator. Dieser liefert neben dem Kategorienvorschlag einen Konfidenzwert.

Liegt die Konfidenz unter einem festgelegten Schwellwert (Größenordnung 0,6 bis 0,8, empirisch auf einem Validierungsdatensatz kalibriert), greift die dritte Stufe: Die Transaktion wird als „unkategorisiert" markiert und dem Nutzer zur manuellen Zuordnung vorgelegt. Jede manuelle Entscheidung fließt zurück in das Händlergedächtnis und in den Trainingsdatenbestand, sodass das System mit der Zeit besser wird.

## Datenaufbereitung

Als Eingabetext für das Modell dient die Zusammenführung von Empfängername und Verwendungszweck. Vor dem Training wird der Text bereinigt: Kundennummern, Mandatsreferenzen, Datumsangaben und ähnliches technisches Rauschen werden entfernt oder durch Platzhalter ersetzt, damit das Modell inhaltliche Muster lernt statt zufälliger Zeichenketten.

Die Trainingsdaten stammen aus bereits manuell kategorisierten Transaktionen — insbesondere aus den bestätigten Zuordnungen des Händlergedächtnisses. Als Startgröße sind etwa 30 bis 100 Beispiele pro Unterkategorie anzustreben. Reicht der Bestand anfangs nicht aus, kann ein Zero-Shot-Verfahren (natürlichsprachliche Inferenz mit einem vortrainierten NLI-Modell) genutzt werden, um Rohdaten vorzuetikettieren; diese Vorschläge werden manuell durchgesehen und bilden dann das erste Trainingsset.

## Training

Der Datenbestand wird stratifiziert in Trainings- und Validierungsdaten aufgeteilt, sodass jede Kategorie in beiden Teilen anteilig vertreten ist. Das Modell wird über mehrere Epochen trainiert; nach jeder Epoche wird die Güte auf den Validierungsdaten gemessen. Als Auswahlkriterium dient der Macro-F1-Wert, der alle Kategorien gleich gewichtet — so wird verhindert, dass das Modell nur die häufigen Kategorien (etwa Supermarkteinkäufe) gut beherrscht und seltene (etwa Geschenke) vernachlässigt. Am Ende wird derjenige Zwischenstand übernommen, der auf den Validierungsdaten am besten abschneidet; das begrenzt zugleich die Gefahr der Überanpassung.

Nach dem Training wird die Trefferquote je Kategorie einzeln betrachtet. Kategorien mit schwachen Werten deuten auf zu wenige oder zu uneinheitliche Trainingsbeispiele hin und werden gezielt nachetikettiert.

Der Rechenaufwand ist gering: Bei einigen tausend Beispielen dauert das Training auf einem gewöhnlichen Desktop-Prozessor wenige Minuten. Das Training kann daher regelmäßig (etwa monatlich oder nach einer bestimmten Zahl neuer manueller Zuordnungen) wiederholt werden.

## Inferenz im laufenden Betrieb

Im Alltagsbetrieb wird das gespeicherte Modell lokal geladen. Jede neue, dem Händlergedächtnis unbekannte Transaktion wird bereinigt, durch das Modell geschickt und erhält Kategorie und Konfidenzwert. Die Antwortzeit liegt im Millisekundenbereich, sodass auch ein kompletter Kontoauszug mit hunderten Buchungen praktisch verzögerungsfrei verarbeitet wird.

## Wartung und Weiterentwicklung

Das System ist als lernender Kreislauf angelegt: Nutzerkorrekturen verbessern kontinuierlich Datenbestand und Händlergedächtnis, regelmäßiges Nachtraining hält den Klassifikator aktuell — etwa wenn neue Händler, geänderte Buchungstexte oder neue Kategorien hinzukommen. Neue Unterkategorien erfordern lediglich neue Trainingsbeispiele und ein Nachtraining; an der Architektur ändert sich nichts. Der Konfidenzschwellwert wird gelegentlich überprüft und so eingestellt, dass die Balance zwischen Automatisierungsgrad und Fehlerrate den eigenen Ansprüchen entspricht.