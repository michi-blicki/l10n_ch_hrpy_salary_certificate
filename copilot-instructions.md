# Copilot Instructions – `l10n_ch_hrpy_salary_certificate`

## 1) Ziel dieses Dokuments
Dieses Dokument definiert die verbindlichen fachlichen und technischen Leitplanken für die Entwicklung des Odoo-Addons `l10n_ch_hrpy_salary_certificate` (Odoo 18 Community Edition).

**Wichtig:**
- In dieser Phase wird **nur Spezifikation/Planung** gemacht.
- Keine produktiven Implementierungen außerhalb der explizit angeforderten nächsten Entwicklungsschritte.

---

## 2) Produktziel (fachlich)
Das Addon erweitert `hr_contract` und `payroll`, um den **Schweizer Lohnausweis** pro Mitarbeitenden zu erzeugen.

Kernanforderungen:
1. Ein HR Payroll Specialist kann für **jedes Feld im Lohnausweis-PDF** eine **Formel** hinterlegen.
2. Formeln müssen auf Odoo-Payroll-Daten (insbesondere Lohnarten/Salary Rules) zugreifen können.
3. Der Lohnausweis wird **pro Mitarbeiter und Jahr** erzeugt (nicht pro Vertrag).
4. Werte müssen bei Bedarf **vertragsübergreifend** aggregiert werden.
5. Generierte Lohnausweise werden in der Datenbank abgelegt.
6. Pro Mitarbeiter+Jahr darf es nur einen aktuellen Lohnausweis geben; eine Neugenerierung ist nur als **Ersatz** (Version/Überschreiben mit Nachvollziehbarkeit) zulässig.
7. In `hr.employee` Formansicht gibt es einen Button zur Lohnausweis-Liste.
8. Der Lohnausweis wird pro Kalenderjahr und Mitarbeiter generiert und nicht auf Basis des Geschäftsjahres oder anderer Zeiträume.
9. Ein Lohnausweis, welcher 3 Kalenderjahre alt ist, wird automatisch archiviert. Archivierte Lohnausweise werden nicht mehr in der Liste der aktiven Lohnausweise angezeigt, können aber über die Historie eingesehen und heruntergeladen werden.
10. Ein Lohnausweis, welcher mehr als 10 Jahre alt ist, wird automatisch gelöscht. Es verbleiben lediglich die Referenzen im Audit-Log, um die Nachvollziehbarkeit zu gewährleisten.
11. In der List View werden standardmäßig nur "Confirmed" Lohnausweise angezeigt. Über einen Filter können auch "Replaced" Lohnausweise sichtbar gemacht werden, um die Historie nachvollziehen zu können. "Draft" Lohnausweise sind nur für den Ersteller sichtbar und dienen als Arbeitsversionen, bis sie bestätigt werden.
12. Das Addon muss inhaltlich konform zur Wegleitung 2026 sein, insbesondere zu Kapitel I (Notwendige Angaben) und Kapitel II (Nicht zu deklarierende Leistungen).

---

## 3) Zielplattform und Abhängigkeiten
- Odoo: **18.0 Community Edition**
- Muss-Dependencies (mindestens):
  - `hr`
  - `hr_contract`
  - `payroll`
  - `mail` (für Chatter/Audit empfohlen)
- Modulname: `l10n_ch_hrpy_salary_certificate`
- Sprache UI/Labels initial: Englisch (i18n-ready, aber keine Mehrsprachigkeit im MVP)

---

## 4) Verbindliche Datenquellen
Primäre Quellen für Berechnungen:
- Mitarbeitende (`hr.employee`)
- Verträge (`hr.contract`) – mehrere Verträge pro Mitarbeiter berücksichtigen
- Lohnabrechnungen (`hr.payslip`) und Zeilen (`hr.payslip.line`)
- Payroll-Regeln/Lohnarten (`hr.salary.rule`, Codes/Struktur)

Grundsatz:
- Zeitliche Filterung erfolgt primär über das gewählte Steuer-/Kalenderjahr.
- Es müssen nur **relevante, finalisierte** Payroll-Daten einfließen. Als finalisiert gelten Payslips, welche den Status "Done" haben. Payslips in den Status "Draft", "Waiting" und "Rejected" dürfen nicht in die Berechnung einbezogen werden.
- Berechnung und Generierung erfolgen **ausschließlich pro Kalenderjahr**; abweichende Geschäftsjahre oder freie Zeiträume sind nicht zulässig.
- Es gilt der Wegleitungsgrundsatz, dass sämtliche Leistungen aus dem Arbeitsverhältnis zu deklarieren sind, soweit sie nicht explizit unter die Ausnahmen der Wegleitung (Kapitel II / Rz 72) fallen.

---

## 5) PDF-Basis und Feldabbildung
PDF-Vorlage liegt in:
- `docs/dbst-form-11lohna-rechts-dfe-de.pdf`
- `docs/dbst-form-11lohna-rechts-dfi-de.pdf`

Weiteres Referenzmaterial im Modul:
- `docs/dbst-form-lohna-wegleitung-2026-de.pdf` (offizielle Erklärung des Formulars und der Felder)

Anforderung:
- Es muss im Mitarbeitersatz (`hr.employee`) ein Boolean-Feld geben, das angibt, ob ein Lohnausweis benötigt wird (z. B. `needs_salary_certificate`).
- Das Feld `needs_salary_certificate` ist fachlich verpflichtend für Mitarbeitende mit sozialversicherungspflichtigen Abzügen. Die automatische Setzung dieses Flags wird durch ein separates, späteres Addon sichergestellt; dieses Modul nutzt das Feld als fachliche Voraussetzung.
- Es muss ein **konfigurierbares Feldmapping** geben, das jedem PDF-Feld eine Berechnungsformel zuordnet. Die PDF-Vorlage darf nicht direkt modifiziert werden, sondern die Feldwerte müssen über die Formel-Engine berechnet und in das PDF eingebettet werden.
- **Alle PDF-Felder der Vorlage sind Pflichtfelder im Mapping.** Für jedes Feld muss eine Formel hinterlegt sein (auch wenn das Ergebnis statisch oder leer ist).
- Die Feldbelegung muss die Wegleitungslogik abbilden: Pflichtangaben aus Kapitel I sind vollständig zu unterstützen; nicht deklarierende Leistungen gemäss Kapitel II dürfen nicht fälschlich als steuerbarer Betrag ausgewiesen werden.
- Feldidentifikatoren müssen stabil gespeichert werden (z. B. technischer Feldcode).
- Ausgabe muss reproduzierbar sein (gleiche Eingangsstände → gleiche Werte).
- Eine Form-View für die Konfiguration der Formeln muss in payroll unter "Configuration → Salary Certificate Formulas" angelegt werden.
- Ein Menu "Salary Certificates" mit zugehöriger List View muss in Payroll vor dem Menu "Configuration" angelegt werden. Die List View zeigt alle generierten Lohnausweise mit Gruppierungs- und Filtermöglichkeiten nach Jahr, Mitarbeiter, Status.
- Lohnausweise können als PDF heruntergeladen werden. Als Weiterentwicklung können Lohnausweise auch per E-Mail versendet werden, aber das ist nicht Teil des ersten MVP.


---

## 6) Formel-Engine (fachliche Spezifikation)
Ziel: HR Payroll Specialist kann Formeln pflegen, ohne Python-Code in Modulen anzupassen.

Mindestanforderungen:
1. Formel je Lohnausweis-Feld konfigurierbar.
2. Formeln dürfen auf vordefinierte Kontexte zugreifen, z. B.:
   - `employee`
   - `year`
   - `contracts`
   - `payslips`
   - Hilfsfunktionen für Summen über Lohnarten (nach Rule Code).
3. Sichere Auswertung (kein beliebiger Code-Exec).
4. Fehler in Formeln müssen klar ausgewiesen werden (inkl. Feldbezug), ohne stilles Verschlucken.
   - Bei Formel-/Validierungsfehlern wird die Generierung nicht bestätigt; es erfolgt eine verständliche Fehlermeldung mit Feldbezug.
5. Optionaler Test-/Vorschau-Modus für Formeln ist als künftige Weiterentwicklung denkbar.
6. In Anlehnung an die Funktionalität der Lohnarten-Berechnung, können Formeln feste Beträge, Prozentsätze, einfache Feldzuweisungen, Aggregationen oder komplexer Python Code beinhalten.
7. Es gibt **keine vordefinierte Zuordnung von Salary Rule Codes zu PDF-Feldern**. Der HR Payroll Specialist definiert die fachliche Zuordnung vollständig über die Formeln.
8. Die Formel-/Regellogik muss die Deklarationsschwellen und Ausnahmen der Wegleitung unterstützen (insbesondere Kapitel II / Rz 72 sowie Schwellenlogik für Angaben in den Ziffern 2.3 und 15).

Nicht-Ziel:
- Kein freier Zugriff auf Dateisystem/Netzwerk/OS durch Formeln.

---

## 7) Ziel-Datenmodell (Leitbild für Implementierung)
Die finalen Modellnamen können in Phase 2 präzisiert werden; fachlich erforderlich sind:

1. **Lohnausweis-Konfiguration (Template/Definition)**
   - Gültigkeit (Jahr, Version)
   - Felddefinitionen mit Reihenfolge

2. **Felddefinition / Feldformel**
   - PDF-Feldschlüssel
   - Fachlabel
   - Formeltext
   - Datentyp/Formatierungsregeln (Währung, Zahl, Text)

3. **Generierter Lohnausweis (pro Mitarbeiter+Jahr)**
   - Referenz auf `hr.employee`
   - Jahr
   - Status (Draft/Confirmed/Replaced/Archived)
   - Generierter PDF-Blob/Attachment
   - Snapshot der berechneten Feldwerte (Audit)
   - Erstellt-von / Erstellt-am / Ersetzt-von / Ersetzt-am (Versionierungskette)

4. **Optional: Rechen-/Generierungslog**
   - Pro Lauf protokollieren: Datenbasis, Fehler, Zeitstempel

---

## 8) Geschäftsregeln (verbindlich)
1. **Eindeutigkeit:** pro `(employee_id, year)` ist maximal **ein** Lohnausweis im Status `Confirmed` erlaubt.
   - Zusätzlich ist maximal **ein** offener `Draft` pro `(employee_id, year)` erlaubt.
   - Historische Versionen in `Replaced`/`Archived` sind mehrfach zulässig.
2. **Ersetzungspflicht:** existiert bereits ein Dokument, darf ein neues nur als Ersatz generiert werden.
   - Neue Ersatzversion startet als `Draft`.
   - Bei Bestätigung der neuen Version wird diese `Confirmed`.
   - Die zuvor `Confirmed`-Version wird automatisch auf `Replaced` gesetzt.
3. **Aggregationsregel:** Berechnung erfolgt mit allen relevanten Verträgen des Mitarbeitenden im Jahr.
4. **Fachliche Voraussetzung:** Generierung ist nur zulässig, wenn `employee.needs_salary_certificate = True`.
5. **Nachvollziehbarkeit:** frühere Version darf nicht unbemerkt verschwinden (Audit-Historie).
6. **Datenkonsistenz:** Generierung darf keine Payroll-Basisdaten verändern.
7. **Wegleitungs-Konformität:** Pflichtangaben (Kapitel I) und Nicht-Deklarationsregeln (Kapitel II) sind als fachliche Validierungsregeln vor Bestätigung zu prüfen.
8. **Ersatzvermerk:** Bei Ersetzung eines bereits ausgestellten Lohnausweises ist im Bemerkungsfeld (Ziffer 15) der Hinweis gemäss Wegleitung aufzunehmen: `Dieser Lohnausweis ersetzt den Lohnausweis vom XX.XX.XXXX`.

---

## 9) UI/UX-Mindestumfang (für Phase 2)
1. **Button in `hr.employee` Form**
   - Öffnet gefilterte Liste der Lohnausweise des Mitarbeitenden.

2. **Listen-/Formansicht Lohnausweise**
   - Filter auf Jahr, Status, Mitarbeiter.
   - Standardmäßig werden nur `Confirmed` Lohnausweise angezeigt.
   - `Replaced` Lohnausweise sind über expliziten Filter sichtbar (Historie).
   - `Draft` Lohnausweise sind nur für den Ersteller sichtbar.
   - Sichtbarkeit der Ersetzungshistorie.

3. **Konfiguration Feldformeln**
   - Pflegbare Ansicht für Feldmapping + Formeln.

4. **Generierungsaktion**
   - Manuell pro Mitarbeiter+Jahr.
   - Ersetzungsdialog/-mechanismus bei bestehendem Dokument.
   - Im `hr.employee`-Formular zusätzlicher Button zur Generierung eines neuen Lohnausweises für das vergangene Jahr oder das aktuelle Jahr. Für die Generierung soll ein Wizard implementiert werden, der die Auswahl des Jahres ermöglicht und bei bestehendem Lohnausweis eine Warnung mit der Option zum Ersetzen anzeigt. Dieser soll zudem die Formeln prüfen und auf Fehler vor der Generierung hinweisen.
   - Generierte PDF dürfen so lange geändert werden, bis sie bestätigt werden (Status "Confirmed"). Nach Bestätigung ist eine Änderung nur noch über die Ersatzfunktion möglich.

Hinweis: UX bewusst minimal halten, kein Scope-Creep.

5. **Lebenszyklus / Aufbewahrung**
   - Lohnausweise, die älter als 3 Kalenderjahre sind, werden automatisch auf `Archived` gesetzt.
   - Archivierte Lohnausweise werden nicht in der aktiven Standardliste gezeigt, bleiben aber über Historie einsehbar und herunterladbar.
   - Lohnausweise, die älter als 10 Jahre sind, werden automatisch gelöscht.
   - Für gelöschte Lohnausweise bleiben Audit-Referenzen zur Nachvollziehbarkeit erhalten.
   - Das Alter bezieht sich auf das Feld `year` des Lohnausweises im Vergleich zum aktuellen Kalenderjahr.

---

## 10) Sicherheit und Rechte
Gruppen:
- payroll.group_payroll_manager (HR Payroll Specialist)
- payroll.group_payroll_user (HR Payroll User)

Zusätzlich:
- Zugriff auf Lohnausweise nach üblichen HR-Record-Rules einschränken.
- Die Rechte sollen auf das absolute Minimum beschränkt werden. Normale Benutzer (base_user) sollen keinen Zugriff auf Lohnausweise oder deren Konfiguration haben.
- HR Payroll User können Lohnausweise generieren und einsehen, aber keine Formeln anpassen oder die Konfiguration ändern.

---

## 11) Technische Qualitätsanforderungen
- Odoo-Standards einhalten (Model, Views, Security, Data, i18n).
- Klare, kleine Methoden; keine monolithischen Generatorfunktionen.
- Fehlertexte fachlich verständlich.
- Generierung deterministisch und wiederholbar.
- Testbarkeit berücksichtigen (unit/transaction tests für Kernlogik).
- Wegleitungs-Konformität muss explizit testbar umgesetzt werden (Kapitel I und II als überprüfbare Regeln).
- Da fehlerhafte Lohnausweise rechtliche Folgen haben können (Pflichtverletzung gemäss Wegleitung), sind Plausibilitäts- und Pflichtfeldvalidierungen vor Bestätigung zwingend.

---

## 12) Nicht im Scope (vorerst)
- Automatische ELM/Swissdec-Übermittlung.
- Massenversand per E-Mail.
- Digitale Signatur-Workflows.
- Mehrsprachige/mehrfache Formularvarianten über die minimal nötige Basis hinaus.

---

## 13) Definition of Done für die Entwicklungsphase
Ein Inkrement gilt erst als fertig, wenn:
1. Lohnausweis für Mitarbeiter+Jahr generiert werden kann.
2. Feldwerte werden aus konfigurierten Formeln berechnet.
3. Vertragsübergreifende Aggregation ist nachweisbar korrekt.
4. Existierender Lohnausweis wird nur über definierten Ersetzungsprozess abgelöst.
5. `hr.employee`-Button führt korrekt zur gefilterten Lohnausweisliste.
6. PDF ist in DB als Attachment abgelegt und historisiert.
7. Dokumentation ist OCA-konform und vollständig.
8. Pflichtangaben aus der Wegleitung (Kapitel I) sind vollständig unterstützt und validiert.
9. Nicht zu deklarierende Leistungen (Kapitel II / Rz 72) werden korrekt nicht bzw. nur bei Überschreitung der Grenzwerte deklariert.

---

## 14) Aktueller Projektstatus (Startpunkt)
Der Modulstand ist aktuell ein Standard-Scaffold (Manifest/Model/View/Security-Platzhalter). Die eigentliche Domänenlogik für Schweizer Lohnausweis ist noch zu implementieren.

---

## 15) Arbeitsmodus für Copilot in diesem Repository
Bei zukünftigen Entwicklungsaufgaben:
1. Immer zuerst Scope gegen dieses Dokument prüfen.
2. Änderungen klein und nachvollziehbar halten.
3. Keine stillen Annahmen bei gesetzlichen Feldern; falls unklar, offene Frage dokumentieren.
4. Vor Implementierung migrations-/upgrade-fähige Datenstruktur bevorzugen.
5. Keine Features außerhalb des freigegebenen Scopes ergänzen.

---

## 16) Checkliste für die Implementierung
Empfohlene Abarbeitungsreihenfolge für **Phase 2** (von Umsetzung zu Abnahme):

### 1) Modul-Setup & Security-Basis

#### A) Modul-Grundlagen
- [ ] `__manifest__.py` enthält korrekte Dependencies: `hr`, `hr_contract`, `payroll`, `mail`.
- [ ] Modul-Metadaten (Name, Version, Summary, Data-Files) sind produktionsreif und konsistent.
- [ ] Security-Dateien, Views und ggf. Daten/CRON-Dateien sind im Manifest vollständig registriert.

#### B) Sicherheit & Rechte
- [ ] `payroll.group_payroll_manager`: Formeln konfigurieren + generieren + ersetzen.
- [ ] `payroll.group_payroll_user`: generieren + einsehen, aber keine Formel-/Konfigurationsänderung.
- [ ] `base.group_user` hat keinen Zugriff auf Lohnausweise und Konfiguration.
- [ ] Record Rules sind auf notwendiges Minimum beschränkt.

### 2) Kernmodell & fachliche Guards

#### C) Datenmodell
- [ ] Modell für Lohnausweis-Dokument pro Mitarbeiter+Jahr ist angelegt.
- [ ] Modell für PDF-Felddefinition/Formel-Mapping ist angelegt.
- [ ] Technischer PDF-Feldschlüssel ist stabil und eindeutig gespeichert.
- [ ] Snapshot der berechneten Feldwerte wird pro generierter Version persistiert.
- [ ] PDF wird als Attachment (`ir.attachment`) am Lohnausweis-Datensatz abgelegt.
- [ ] Versionierungsfelder für Ersetzungskette sind vorhanden (`created_by/at`, `replaced_by/at` o. ä.).

#### D) Constraints & Geschäftsregeln
- [ ] SQL-/ORM-Constraint: maximal ein `Confirmed` pro `(employee_id, year)`.
- [ ] SQL-/ORM-Constraint: maximal ein offener `Draft` pro `(employee_id, year)`.
- [ ] Generierung blockiert, wenn `employee.needs_salary_certificate != True`.
- [ ] Ersetzung funktioniert nur über den definierten Ersatzprozess.
- [ ] Bei Bestätigung einer Ersatzversion wird alte `Confirmed`-Version automatisch `Replaced`.
- [ ] Payroll-Basisdaten (`hr.payslip`, `hr.payslip.line`, `hr.contract`) werden nie verändert.
- [ ] Bestätigung eines Lohnausweises ist nur zulässig, wenn Pflichtvalidierungen nach Wegleitung Kapitel I und II erfolgreich sind.

### 3) Berechnung, Formel-Engine & PDF

#### E) Berechnungsbasis
- [ ] Datenfilter berücksichtigt ausschließlich das gewählte Kalenderjahr.
- [ ] Nur Payslips im Status `Done` werden in die Berechnung einbezogen.
- [ ] Payslips in `Draft`, `Waiting`, `Rejected` sind explizit ausgeschlossen.
- [ ] Vertragsübergreifende Aggregation über alle relevanten Mitarbeiterverträge im Jahr ist implementiert.

#### F) Formel-Engine
- [ ] Formel je PDF-Feld ist Pflicht; kein Feld bleibt ohne Formel.
- [ ] Alle PDF-Felder der Vorlage sind im Mapping vorhanden.
- [ ] Kontextobjekte (`employee`, `year`, `contracts`, `payslips`) stehen in Formeln zur Verfügung.
- [ ] Hilfsfunktionen für Lohnarten-Summen (nach Rule Code) sind verfügbar.
- [ ] Keine harte Vordefinition von Salary Rule Codes je Feld (volle Fachflexibilität).
- [ ] Formel-Auswertung ist sicher (kein Dateisystem-/Netzwerk-/OS-Zugriff).
- [ ] Formel-/Validierungsfehler brechen die Bestätigung ab und liefern klare Feldfehlermeldungen.

#### G) PDF-Erzeugung
- [ ] Werte werden in die bestehende PDF-Vorlage eingebettet, ohne die Vorlage selbst zu verändern.
- [ ] Generierte PDFs sind reproduzierbar bei identischem Eingangsstand.
- [ ] Download aus der Lohnausweis-Ansicht ist möglich.

### 4) UI, Lifecycle & Prozessführung

#### H) UI/UX
- [ ] Menü `Salary Certificates` ist im Payroll-Menü vor `Configuration` platziert.
- [ ] List View bietet Gruppierung/Filter nach Jahr, Mitarbeiter, Status.
- [ ] Standardfilter zeigt nur `Confirmed`.
- [ ] Optionaler Filter blendet `Replaced` zur Historie ein.
- [ ] `Draft` ist nur für den Ersteller sichtbar.
- [ ] `Archived` ist nicht Teil der aktiven Standardliste und nur über Historie/Filter sichtbar.
- [ ] Button in `hr.employee` öffnet gefilterte Lohnausweis-Liste des Mitarbeitenden.
- [ ] Zusätzlicher Generate-Button in `hr.employee` startet Wizard.
- [ ] Wizard erlaubt Jahrwahl (aktuelles oder vergangenes Jahr) und zeigt Ersatzwarnung bei bestehendem Dokument.

#### I) Lebenszyklus / Aufbewahrung
- [ ] Automatische Archivierung: Dokumente älter als 3 Kalenderjahre → `Archived`.
- [ ] `Archived` erscheint nicht in der aktiven Standardliste, bleibt aber historisch einseh-/downloadbar.
- [ ] Automatische Löschung: Dokumente älter als 10 Jahre werden entfernt.
- [ ] Audit-Referenzen bleiben trotz Löschung nachvollziehbar erhalten.
- [ ] Altersberechnung basiert auf Lohnausweisfeld `year` vs. aktuelles Kalenderjahr.

### 5) Wegleitungs-Fachcompliance (Formular 11)

#### J) Wegleitungs-Compliance (Kapitel I / II)
- [ ] Pflichtangaben gemäss Wegleitung Kapitel I sind im Modell/Feldmapping explizit abgedeckt (insb. A/B, C, D, E, F, G, H, I, Ziffern 1–15).
- [ ] Kalenderjahr-Logik (Buchstabe D) entspricht Wegleitung; Aufteilung auf mehrere Ausweise wird nicht als Standardfall zugelassen.
- [ ] Logik für Feld F (unentgeltliche Beförderung) und Feld G (Kantinenverpflegung/Lunch-Checks) ist regelbasiert gemäss Wegleitung implementierbar.
- [ ] Gehaltsnebenleistungen in Ziffern 2.1 / 2.2 / 2.3 folgen den Wegleitungsregeln (inkl. Privatanteil Geschäftsfahrzeug und Marktwertprinzip).
- [ ] Spesenlogik in Ziffer 13 unterscheidet korrekt zwischen effektiven Spesen, Pauschalspesen und nicht als Spesen zulässigen Vergütungen.
- [ ] Bemerkungsfeld Ziffer 15 unterstützt alle für dieses Addon relevanten Wegleitungsvermerke (u. a. Ersatz/Rektifikat, Spesenreglement-Hinweis falls verwendet).
- [ ] Rektifikat-Vermerk in Ziffer 15 ist mit dem von der Wegleitung vorgegebenen Wortlaut abbildbar.
- [ ] Nicht zu deklarierende Leistungen gemäss Kapitel II / Rz 72 sind als explizite Ausnahmelogik dokumentiert und testbar umgesetzt.
- [ ] Grenzwerte aus Kapitel II / Rz 72 werden konfigurierbar bzw. klar versioniert gepflegt, damit jährliche Wegleitungsupdates nachvollziehbar übernommen werden können.

### 6) Verifikation, Doku & Go-Live

#### K) Tests & Abnahme
- [ ] Unit-/Transaction-Tests decken Kernlogik (Formeln, Aggregation, Ersetzung, Constraints) ab.
- [ ] Testfall: Mehrere Verträge im gleichen Jahr mit korrekter Summierung.
- [ ] Testfall: erneute Generierung erzwingt Ersatzprozess.
- [ ] Testfall: Formel-Fehler verhindert Bestätigung.
- [ ] Testfall: Sichtbarkeitsregeln (`Confirmed`/`Replaced`/`Draft`) greifen korrekt.
- [ ] Testfall: 3-/10-Jahres-Regeln für Archivierung/Löschung greifen korrekt.
- [ ] Testfall: Wegleitungs-Pflichtangaben werden vollständig befüllt/validiert (Kapitel I).
- [ ] Testfall: Rektifikat-Vermerk in Ziffer 15 wird bei Ersatz korrekt gesetzt.
- [ ] Testfall: Rektifikat-Vermerk verwendet exakt den Wegleitungstext `Dieser Lohnausweis ersetzt den Lohnausweis vom XX.XX.XXXX`.
- [ ] Testfall: Nicht deklarierende Leistungen gemäss Kapitel II / Rz 72 werden korrekt behandelt.
- [ ] Testfall: Bestätigung wird blockiert, wenn Wegleitungs-Validierungen (Kapitel I/II) fehlschlagen.

#### L) Dokumentationspflicht für OCA-Überführung (`l10n-switzerland`)
- [ ] `README.md` ist vollständig und OCA-konform strukturiert (Zweck, Installation, Konfiguration, Nutzung, bekannte Einschränkungen, Changelog/History).
- [ ] Funktionale Konfiguration der Formeln und der Generierungsprozess (inkl. Ersatzfall) sind nachvollziehbar dokumentiert.
- [ ] Sicherheits- und Rechtekonzept (Gruppen, Sichtbarkeit, Record Rules) ist explizit beschrieben.
- [ ] Datenaufbewahrung (3 Jahre Archivierung, 10 Jahre Löschung, Audit-Referenzen) ist klar dokumentiert.
- [ ] Entwicklerdokumentation beschreibt Datenmodell, Statusübergänge und zentrale Geschäftsregeln für Reviews im OCA-Kontext.
- [ ] Testdokumentation listet mindestens die in Abschnitt K definierten Kern-Testfälle und deren erwartetes Verhalten.
- [ ] Lizenz- und Metadatenangaben sind konsistent zu OCA-Anforderungen (z. B. Lizenz, Maintainer, Abhängigkeiten, Modulbeschreibung).

#### M) Go-Live-Readiness
- [ ] Alle Punkte aus Kapitel 13 (Definition of Done) sind objektiv nachweisbar erfüllt.
- [ ] Keine Implementierung außerhalb des freigegebenen Scopes aus Kapitel 12.
- [ ] Dokumentation und Fehlermeldungen sind fachlich verständlich für Payroll-Anwender.
- [ ] Fachlicher Abgleich gegen `docs/dbst-form-lohna-wegleitung-2026-de.pdf` ist dokumentiert und freigegeben.

### 7) Harte Abnahme-Gates (Blocker)

#### N) Blockierende Freigabekriterien
- [ ] Kein Lohnausweis kann auf `Confirmed` gesetzt werden, wenn eine Pflichtregel aus Kapitel D, F, J oder ein Test aus Abschnitt K fehlschlägt.
- [ ] Alle als Wegleitungs-kritisch markierten Testfälle (Kapitel I/II, Rektifikat, Spesenlogik, Nichtdeklarationen) sind grün.
- [ ] Fachliche Freigabe durch Payroll-Verantwortliche für Wegleitungsabgleich ist dokumentiert.

---
## 17) Offene Punkte für die nächste Abstimmung 
Aktuell bestehen auf Basis der bereits beantworteten Fragen **keine offenen fachlichen Punkte** zum gewünschten Funktionsumfang.

---

## 18) Gap-Analyse (Code vs. Anforderungen Kapitel 1–15 und 16.1–16.5)

Stand der Prüfung: 21.02.2026 (vollständiger Review des Source Codes im Modulverzeichnis).

### A) Kritische Abweichungen (Blocker)

1. **Rektifikat-/Ersatzvermerk Ziffer 15 verwendet nicht den geforderten Wegleitungstext**
   - Anforderung: Kapitel 8.8 sowie 16.J (exakter Wortlaut: `Dieser Lohnausweis ersetzt den Lohnausweis vom XX.XX.XXXX`).
   - Ist: Implementierung erzeugt aktuell englischen Text (`This salary certificate replaces ...`).
   - Folge: Formale Nicht-Konformität zur Wegleitungsvorgabe.

2. **Bestätigte Lohnausweise sind weiterhin editierbar**
   - Anforderung: Kapitel 9.4 (nach `Confirmed` nur Änderung über Ersatzfunktion).
   - Ist: Keine serverseitige Guard in `write()`/State-Transition; direkte Änderungen an bestätigten Datensätzen sind möglich.
   - Folge: Prozess- und Audit-Verletzung möglich.

3. **State-Übergänge nicht hart abgesichert (Umgehung von `action_confirm`)**
   - Anforderung: Kapitel 8.2/8.7, 16.D/N (Bestätigung nur bei erfolgreichen Validierungen).
   - Ist: Kein Schutz gegen direktes `write({'state': 'confirmed'})`.
   - Folge: Compliance-, Ersatz- und Validierungslogik kann umgangen werden.

4. **Wegleitungs-Compliance Kapitel I/II nur teilweise/feldplatzhalter-basiert umgesetzt**
   - Anforderung: Kapitel 2.12, 8.7, 11, 16.J (vollständige Abdeckung Pflichtangaben + Ausnahmen).
   - Ist: Regel-Framework vorhanden, aber Presets/Feldschlüssel sind generisch und decken die vollständige Wegleitungslogik (A/B/C... Ziffern 1–15, F/G, Spesenlogik etc.) nicht nachweisbar vollständig ab.
   - Folge: Fachliche Freigabekriterien aus Kapitel 16.J/N nicht erfüllt.

### B) Wesentliche fachliche/technische Lücken

5. **Sprache im Code weiterhin nicht konsistent Englisch**
   - Anforderung: Kapitel 3 (UI/Labels initial Englisch).
   - Ist: In mehreren Modell-Hilfetexten sind weiterhin deutsche Strings enthalten.
   - Folge: Inkonsistente UI/Entwicklungsbasis, i18n-Basis nicht sauber.

6. **Formel-Mapping-Vollständigkeit hängt an `required_in_template` statt strikt „alle PDF-Felder“**
   - Anforderung: Kapitel 5 (alle PDF-Felder Pflicht im Mapping).
   - Ist: Constraint prüft nur aktive Felder mit `required_in_template=True`.
   - Folge: Potenzielle Lücke zur „alle Felder“-Pflicht bei falsch gepflegten Katalogeinträgen.

7. **Template-Formelkonfiguration liegt nicht eindeutig unter Payroll → Configuration**
   - Anforderung: Kapitel 5/9.3 (explizite Platzierung unter Configuration).
   - Ist: Menüstruktur ist unter Payroll vorhanden, aber Configuration-Pfad nicht klar/technisch erzwungen.
   - Folge: Abweichung vom geforderten Navigationsziel.

8. **HR-Record-Rule-Einschränkung nicht vollständig nach „üblichen HR-Record-Rules“ abgebildet**
   - Anforderung: Kapitel 10.
   - Ist: Es gibt primär Draft-Owner-Rule; feinere HR-Sichtbarkeitsregeln (z. B. nach Company/HR-Zuständigkeit) fehlen.
   - Folge: Rechtebild kann zu breit sein.

9. **Aufbewahrung/Löschung ohne explizite Bereinigung zugehöriger PDF-Attachments**
   - Anforderung: Kapitel 9.5/16.I (Dokumente >10 Jahre entfernen).
   - Ist: Zertifikatsdatensatz wird gelöscht; Attachment-Lifecycle ist nicht explizit garantiert bereinigt.
   - Folge: Datenreste/Storage-Leaks möglich.

10. **Reproduzierbarkeit der PDF-Ausgabe nicht nachweisbar abgesichert**
    - Anforderung: Kapitel 5/16.G (gleicher Input → gleiche Ausgabe).
    - Ist: Technisch angestrebt, aber kein harter Nachweis (z. B. deterministische Writer-Metadaten + Tests).
    - Folge: Auditierbarkeit eingeschränkt.

### C) Fehlende Nachweise für Enterprise-/Abnahme-Niveau

11. **Keine automatisierten Tests (Unit/Transaction) für Kernlogik**
    - Anforderung: Kapitel 11, 16.K, 16.N.
    - Ist: Keine Testabdeckung für Constraints, Ersetzung, Validierung, Lifecycle, Sichtbarkeit, Kapitel I/II.
    - Folge: Abnahme-Gates aus 16.K/N objektiv nicht erfüllbar.

12. **Dokumentation deutlich unvollständig (README/OCA-Readiness)**
    - Anforderung: Kapitel 13.7, 16.L.
    - Ist: `README.md` ist aktuell nur ein Einzeiler.
    - Folge: OCA-konforme Überführung/Review nicht möglich.

13. **Wegleitungsabgleich (2026) nicht dokumentiert/freigegeben**
    - Anforderung: Kapitel 16.M/N.
    - Ist: Kein dokumentierter fachlicher Abgleich gegen die Referenzunterlagen im Modul.
    - Folge: Fachliche Go-Live-Freigabe fehlt.

### D) Checkliste 16.1–16.5: verbleibende offene Punkte (konsolidiert)

- **16.1 (Security-Basis):** HR-Record-Rule-Minimum/Feingranularität unvollständig.
- **16.2 (Kernmodell/Guards):** Bestätigungs- und Änderungs-Guards nicht manipulationssicher; Ersatzprozess nicht vollständig write-sicher erzwungen.
- **16.3 (Berechnung/Engine/PDF):** Vollständige Wegleitungsfeldabdeckung, harte Reproduzierbarkeitsnachweise und eindeutige Pflichtfeldgarantie noch nicht final.
- **16.4 (UI/Lifecycle):** Configuration-Platzierung nicht eindeutig; Attachment-Lifecycle bei 10-Jahres-Löschung offen.
- **16.5 (Wegleitungs-Compliance):** Fachlogik für Kapitel I/II nur teilweise konkretisiert; kritische Regeln (u. a. Ziffern 2.1/2.2/2.3, 13, 15 inkl. exaktem Rektifikat-Text) nicht vollständig nachweisbar implementiert.
