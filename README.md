# Dateiexperte

![Logo](logo.jpg) Ein benutzerfreundliches Python-Programm mit grafischer Oberfläche (GUI) zum Sortieren und Verwalten von Dateien auf Ihrem Computer (getestet unter Linux und Windows).

## Beschreibung

Der Dateiexperte hilft Ihnen dabei, Ordnung in Ihren Ordnern zu schaffen. Sie können ein Quellverzeichnis auswählen, und das Programm sortiert die darin enthaltenen Dateien (optional rekursiv durch Unterordner) basierend auf konfigurierbaren Regeln in ein Zielverzeichnis. Dabei werden die Dateien in Ordner entsprechend ihrer Kategorie (z.B. "Bilder", "Dokumente") und optional weiter in Unterordner entsprechend ihres Dateityps (z.B. "jpg", "pdf") kopiert oder verschoben. Bestimmte Dateitypen und Ordnernamen können vom Sortiervorgang ausgeschlossen werden.

## Funktionen

* **Grafische Benutzeroberfläche (GUI):** Einfache Bedienung über eine Tkinter-basierte Oberfläche.
* **Quell-/Zielordner-Auswahl:** Bequeme Auswahl der zu verarbeitenden Ordner über Dialogfenster.
* **Kopieren oder Verschieben:** Wahlmöglichkeit, ob Dateien kopiert oder verschoben werden sollen.
* **Regelbasierte Sortierung:** Sortiert Dateien anhand ihrer Endungen in konfigurierbare Kategorien.
* **Typ-Unterordner:** Erstellt automatisch Unterordner für spezifische Dateiendungen innerhalb der Kategorieordner (z.B. `Dokumente/pdf/`, `Bilder/jpg/`).
* **Konfigurierbare Kategorien:** Einfache Verwaltung der Zuordnung von Dateiendungen zu Kategorien über eine Einstellungs-GUI oder direkt in der `sorter_config.json`-Datei.
* **Konfigurierbare Ausschlüsse:**
    * **Dateiendungen:** Schließen Sie bestimmte Dateitypen (z.B. `.tmp`, `.ini`) vom Sortieren aus.
    * **Ordnernamen:** Ignorieren Sie bestimmte Ordnernamen (z.B. `.git`, `temp`, `Archiv`) und deren Inhalte während des Scanvorgangs.
* **Editor für Einstellungen:** Ein integrierter Editor (über das Menü "Einstellungen") mit Tabs zur Verwaltung von:
    * Kategorien und deren zugehörigen Dateiendungen.
    * Der Liste der ausgeschlossenen Dateiendungen.
    * Der Liste der ignorierten Ordnernamen.
* **Datei-Informationen:** Zeigt detaillierte Systeminformationen (Pfad, Größe, Daten etc.) zu einer ausgewählten Datei an (Menü "Bearbeiten").
* **Fortschrittsanzeige & Logging:** Zeigt den Fortschritt des Sortiervorgangs an und protokolliert Aktionen sowie Fehler im Hauptfenster.
* **Konfigurationsdatei:** Speichert alle Einstellungen in einer lesbaren `sorter_config.json`-Datei.
* **Plattformunabhängigkeit:** Entwickelt mit Python und Tkinter, sollte auf den meisten Systemen (Linux, Windows, macOS) laufen (getestet unter Linux/Windows).

## Screenshots

![Hauptfenster Dateiexperte](img/Screenshot_Hauptfenster.png)
*Das Hauptfenster der Anwendung.*

![Einstellungsfenster - Kategorien Tab](img/Screenshot_Kategorien.png)
*Bearbeiten der Kategorien und Dateiendungen.*

![Einstellungsfenster - Ausschlüsse Tab](img/Screenshot_AusgeschlosseneEndungen.png)
*Verwaltung der ausgeschlossenen Endungen.*

![Einstellungsfenster - Ignorierte Ordner](img/Screenshot_IgnorierteOrdner.png)
*Verwaltung der ignorierten Ordner.*

![Datei-Info Dialog](img/ScreenshotInfo.png)
*Anzeige detaillierter Datei-Informationen.*

```markdown