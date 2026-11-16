# Arbeitsstand der Praxisphase

ServicePulse verbindet historische Serviceeinträge mit den veröffentlichten Betriebsdaten von Ultratiefkühlgeräten. Die Praxisphase untersucht die Qualität dieser Daten und vergleicht die Kammertemperatur vor dokumentierten Serviceereignissen mit Vergleichswochen desselben Geräts.

## Was sich in der App geändert hat

- Die Übersicht zeigt Serviceeinträge, Zeitverteilung und Fehlerkategorien. In der Geräteverwaltung lassen sich eigene Berichte archivieren und wiederherstellen. Historische Forschungsberichte sind vor der Archivierung geschützt.
- Die Betriebsanalyse bietet Einzelfälle für Temperaturveränderung, Messlücke und Datumswiderspruch. Sie zeigt Messabdeckung und Lücken. Ein Klick hebt den aktuell geöffneten Fall hervor. Im Diagramm lässt sich ein Zeitraum vergrößern.
- Der Präsentationsmodus zeigt die drei Hauptbereiche. Über **Ansicht** lässt sich zusätzlich **Datenqualität & Forschung** öffnen.

## Eigene Untersuchungen

| Untersuchung | Vorgehen und Ergebnis |
| --- | --- |
| Datenqualität | Für 53 Geräte wurden die Temperaturzeitstempel geräteweise ausgewertet. Der häufigste Abstand beträgt 60 Sekunden bei Revco und 360 Sekunden bei Haier. Mit der Regel ab zehn typischen Intervallen und Prüfung kurzer Nachbarabstände ergaben sich 833 deutliche Aufzeichnungslücken bei Revco und zwei bei Haier. An 121 gerätebezogenen Zeitpunkten gab es mehrere Zeilen. Bei 104 davon unterschieden sich die Temperaturwerte. |
| Serviceereignisse | Die historische Liste enthält 46 dokumentierte Einträge auf 24 Revco-Geräten. Nach Quellen- und Abdeckungsprüfung blieben 21 Kandidaten. Für 18 Fälle auf 13 Geräten ließ sich eine geeignete Vergleichswoche zuordnen. |
| Temperaturvergleich | Die sieben vollen Tage vor dem dokumentierten Servicetag wurden mit einer anderen Woche desselben Geräts verglichen. Bei 1 °C Anstieg zwischen benachbarten Stundenmitteln wurden 12 Erwärmungsepisoden vor Service gezählt. In den Referenzen waren es fünf ohne zusätzlichen Filter für Gerätemeldungen und null mit Filter. |

Die beobachtete Häufung ist von der Wahl der Vergleichswochen und von einzelnen Geräten abhängig. Nach Ausschluss der drei einflussreichsten Geräte stehen bei 1 °C zwei Episoden vor Service fünf Episoden in den Referenzen ohne zusätzlichen Logfilter gegenüber. Der Vergleich ist rückblickend und trägt kein allgemeines Vorwarnmuster. Ein dokumentierter Servicetag ist ein Zeitanker der Auswertung. Der technische Fehlerbeginn kann früher liegen.

Die App zeigt den Verlauf um einen Servicetag für einzelne Geräte. Die fallübergreifende Auswertung der 18 Paare und die Robustheitsprüfung wurden gesondert durchgeführt. Datenquelle ist der [veröffentlichte Datensatz von Huang et al.](https://doi.org/10.1038/s41597-023-02808-6). Hinweise zur lokalen Einrichtung stehen in der [Startanleitung](../README.md#start-unter-windows) und im [Datenimport](datenimport.md).
