# -*- coding: utf-8 -*-
"""
Dateiexperte v1.10.1 (2025-04-20)
Sortiert Dateien in einem Quellverzeichnis basierend auf Konfigurationsregeln
in ein Zielverzeichnis. Erstellt Kategorieordner und darin optional
Unterordner basierend auf der Dateiendung. Bietet Datei-Info-Funktion
und editierbare Ausschlussmöglichkeit für Dateiendungen und Ordnernamen.

Benötigt: Pillow (`pip install Pillow`) für Logo-Anzeige.
           `logo.jpg` im selben Verzeichnis.
           `sorter_config.json` (wird automatisch erstellt).
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext, simpledialog
import os
import shutil
import threading
import json
import copy
import datetime
# import time # Wird nicht mehr direkt benötigt
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False # Flag setzen, wenn Pillow nicht installiert ist

# -----------------------------------------------------------------------------
# Hauptanwendungsklasse
# -----------------------------------------------------------------------------
class FileSorterApp:
    """
    Hauptklasse für die Dateiexperte-Anwendung mit GUI.
    """
    CONFIG_FILENAME = "sorter_config.json" # Einfache Struktur wird erwartet
    APP_VERSION = "1.10.1" # Aktuelle Version

    def __init__(self, master):
        """
        Initialisiert die Hauptanwendung.

        Args:
            master: Das Tkinter-Hauptfenster (root).
        """
        self.master = master
        self.current_year = datetime.date.today().year
        # *** Änderung: Fenstertitel geändert ***
        master.title("Dateiexperte")
        master.geometry("650x500")
        master.minsize(600, 450) # Mindestgröße

        # --- Menüleiste erstellen ---
        menubar = tk.Menu(master)
        master.config(menu=menubar)

        # --- Bearbeiten-Menü ---
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Bearbeiten", menu=edit_menu)
        edit_menu.add_command(label="Datei-Info...", command=self.show_file_info)

        # --- Einstellungen-Menü ---
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Einstellungen", menu=settings_menu)
        settings_menu.add_command(label="Kategorien & Ausschlüsse bearbeiten...", command=self.open_category_editor)

        # --- Info-Menü ---
        info_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Info", menu=info_menu)
        info_menu.add_command(label="Info / Copyright", command=self.show_info_window)

        # --- Hauptframe & Status Text ---
        main_frame = ttk.Frame(master, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        self.status_text = scrolledtext.ScrolledText(main_frame, height=12, width=80, state='disabled', wrap=tk.WORD)

        # --- Konfiguration laden (einfache Struktur + Ausschlüsse) ---
        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.CONFIG_FILENAME)
        self.categories = {}
        self.extension_to_category = {}
        self.default_category_name = "_Unsortiert"
        self.excluded_extensions = set() # Set für Endungs-Ausschlüsse
        self.excluded_folders = set()    # Set für Ordner-Ausschlüsse
        self.load_config() # Lädt Config inkl. beider Ausschlüsse

        # --- Variablen für GUI-Elemente ---
        self.source_dir = tk.StringVar()
        self.target_dir = tk.StringVar()
        self.operation_type = tk.StringVar(value="copy")

        # --- GUI Elemente Layout ---
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1) # Zeile für Log-Fenster

        row_index = 0
        # Quellordner
        ttk.Label(main_frame, text="Quellordner:").grid(row=row_index, column=0, padx=5, pady=5, sticky="w")
        self.source_entry = ttk.Entry(main_frame, textvariable=self.source_dir, width=60)
        self.source_entry.grid(row=row_index, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(main_frame, text="Durchsuchen...", command=self.browse_source).grid(row=row_index, column=2, padx=5, pady=5)
        row_index += 1
        # Zielordner
        ttk.Label(main_frame, text="Zielordner:").grid(row=row_index, column=0, padx=5, pady=5, sticky="w")
        self.target_entry = ttk.Entry(main_frame, textvariable=self.target_dir, width=60)
        self.target_entry.grid(row=row_index, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(main_frame, text="Durchsuchen...", command=self.browse_target).grid(row=row_index, column=2, padx=5, pady=5)
        row_index += 1
        # Aktion
        option_frame = ttk.Frame(main_frame)
        option_frame.grid(row=row_index, column=0, columnspan=3, padx=5, pady=5, sticky="w")
        ttk.Label(option_frame, text="Aktion:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(option_frame, text="Kopieren", variable=self.operation_type, value="copy").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(option_frame, text="Verschieben", variable=self.operation_type, value="move").pack(side=tk.LEFT, padx=5)
        row_index += 1
        # Start-Button
        self.start_button = ttk.Button(main_frame, text="Sortieren starten", command=self.start_sorting_thread, style="Accent.TButton")
        style = ttk.Style(); style.configure("Accent.TButton", foreground="white", background="#0078D7")
        self.start_button.grid(row=row_index, column=0, columnspan=3, pady=15)
        row_index += 1
        # Fortschrittsbalken
        self.progress_bar = ttk.Progressbar(main_frame, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.grid(row=row_index, column=0, columnspan=3, pady=5, padx=5, sticky="ew")
        row_index += 1
        # Log-Label
        ttk.Label(main_frame, text="Status / Log:").grid(row=row_index, column=0, columnspan=3, padx=5, pady=(10,0), sticky="w")
        row_index += 1
        # Log-Fenster
        self.status_text.grid(row=row_index, column=0, columnspan=3, padx=5, pady=(0,10), sticky="nsew")

        # --- Initiales Logging ---
        self.log(f"Dateiexperte gestartet (v{self.APP_VERSION}). Konfig: {self.config_file}") # Name angepasst
        if not PIL_AVAILABLE: self.log("WARNUNG: Pillow nicht gefunden. Logo kann nicht angezeigt werden.")
        self.log(f"Standard-Ziel für Unsortiertes: '{self.default_category_name}'")
        self.log(f"{len(self.extension_to_category)} Dateiendungen Kategorien zugeordnet.")
        if self.excluded_extensions: self.log(f"{len(self.excluded_extensions)} Endungen werden ignoriert.")
        if self.excluded_folders: self.log(f"{len(self.excluded_folders)} Ordnernamen werden ignoriert.")

    # --- Menü-Callbacks ---
    def show_info_window(self):
        """Zeigt das benutzerdefinierte Info-Fenster."""
        if not PIL_AVAILABLE:
             messagebox.showwarning("Pillow fehlt", "Pillow wird benötigt für das Logo.\nInstallieren: pip install Pillow", parent=self.master)
             # Name und Version angepasst
             messagebox.showinfo("Info", f"Dateiexperte v{self.APP_VERSION}\nCopyright {self.current_year} @ Knut Wehr", parent=self.master)
             return
        # InfoWindow Klasse ist weiter unten definiert
        info_window = InfoWindow(self.master, self.current_year, self.APP_VERSION) # Version übergeben

    def open_category_editor(self):
        """Öffnet das Fenster zur Bearbeitung der Kategorien UND Ausschlüsse."""
        # CategoryEditor Klasse ist weiter unten definiert
        editor_window = CategoryEditor(
            self.master,
            self.config_file,
            self.categories,
            self.default_category_name,
            self.excluded_extensions, # Endungs-Ausschlüsse übergeben
            self.excluded_folders     # Ordner-Ausschlüsse übergeben
        )
        self.log("Konfiguration wird nach möglicher Bearbeitung neu geladen...")
        self.load_config() # Lädt Kategorien UND beide Ausschlüsse neu
        self.log(f"Konfiguration neu geladen. {len(self.extension_to_category)} Endungen gemappt, "
                 f"{len(self.excluded_extensions)} Endungen ausgeschlossen, "
                 f"{len(self.excluded_folders)} Ordner ausgeschlossen.")

    def show_file_info(self):
        """Öffnet Dateiauswahldialog und zeigt Infos zur gewählten Datei an."""
        file_path = filedialog.askopenfilename(title="Datei für Info auswählen", parent=self.master)
        if not file_path: return

        try:
            stats = os.stat(file_path)
            info_to_display = {}
            info_to_display["Dateiname"] = os.path.basename(file_path)
            full_path = os.path.abspath(file_path)
            info_to_display["Voller Pfad"] = full_path
            info_to_display["Verzeichnis"] = os.path.dirname(full_path)
            size_str = f"{self.format_size(stats.st_size)} ({stats.st_size:,} Bytes)"
            info_to_display["Größe"] = size_str.replace(",", ".")
            dt_format = "%d.%m.%Y %H:%M:%S"
            try: info_to_display["Erstellt"] = datetime.datetime.fromtimestamp(stats.st_ctime).strftime(dt_format) + " (Metadaten)"
            except OSError: info_to_display["Erstellt"] = "N/A"
            try: info_to_display["Zuletzt geändert"] = datetime.datetime.fromtimestamp(stats.st_mtime).strftime(dt_format)
            except OSError: info_to_display["Zuletzt geändert"] = "N/A"
            try: info_to_display["Zuletzt zugegriffen"] = datetime.datetime.fromtimestamp(stats.st_atime).strftime(dt_format)
            except OSError: info_to_display["Zuletzt zugegriffen"] = "N/A"
            _, extension = os.path.splitext(info_to_display["Dateiname"])
            info_to_display["Dateiendung"] = extension if extension else "(Keine)"

            # Info-Dialog anzeigen (FileInfoDialog Klasse ist weiter unten definiert)
            FileInfoDialog(self.master, info_to_display)

        except FileNotFoundError: messagebox.showerror("Fehler", f"Datei nicht gefunden:\n{file_path}", parent=self.master)
        except PermissionError: messagebox.showerror("Fehler", f"Keine Leseberechtigung für:\n{file_path}", parent=self.master)
        except Exception as e:
            self.log(f"Fehler beim Abrufen der Datei-Info für '{file_path}': {e}")
            messagebox.showerror("Fehler", f"Fehler beim Abrufen der Datei-Informationen:\n{e}", parent=self.master)

    # --- Hilfsfunktion zur Größenformatierung ---
    def format_size(self, size_bytes):
        """Konvertiert Bytes in eine lesbare Größe (KB, MB, GB)."""
        if size_bytes < 0: return "N/A"
        if size_bytes < 1024: return f"{size_bytes} Bytes"
        elif size_bytes < 1024**2: return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024**3: return f"{size_bytes / (1024**2):.2f} MB"
        else: return f"{size_bytes / (1024**3):.2f} GB"

    # --- Config Methoden (mit Ausschlüssen) ---
    def create_default_config(self):
        """Erstellt Standard-Config mit Kategorien, StandardKategorie, AusgeschlossenenEndungen und AusgeschlossenenOrdnern."""
        default_config = {
            "Kategorien": {
                "Bilder": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".heic"],
                "Dokumente": [".pdf", ".docx", ".doc", ".txt", ".odt", ".rtf", ".xlsx", ".xls", ".pptx", ".ppt", ".md"],
                "Musik": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
                "Videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv"],
                "Archive": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
                "Code": [".py", ".java", ".js", ".html", ".css", ".cpp", ".c", ".cs", ".php", ".json", ".xml", ".yaml"],
                "Programme": [".exe", ".msi", ".dmg", ".app", ".deb", ".rpm"],
                "Fonts": [".ttf", ".otf", ".woff", ".woff2"]
            },
            "StandardKategorie": "_Unsortiert",
            "AusgeschlosseneEndungen": [
                ".tmp", ".temp", ".lnk", ".ini", ".sys", ".dll", ".part", ".crdownload",
                ".ds_store", ".localized", "thumbs.db", "desktop.ini"
            ],
            "AusgeschlosseneOrdner": [
                "temp", "tmp", ".git", ".svn", "__pycache__", "archiv", "backup", "sicherung",
                "system volume information", ".trash", ".trash-1000"
            ]
        }
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f: json.dump(default_config, f, indent=4, ensure_ascii=False)
            self.log(f"Standard-Konfigurationsdatei '{self.CONFIG_FILENAME}' erstellt.")
            return default_config
        except OSError as e: self.log(f"FEHLER Erstellen Config: {e}"); messagebox.showerror("Fehler", f"Config nicht erstellt:\n{e}", parent=self.master); return None

    def load_config(self):
        """Lädt Konfig (Kategorien, Standard, Ausschlüsse Endungen & Ordner) und baut Maps."""
        config_data = None; self.categories = {}; self.extension_to_category = {};
        self.excluded_extensions = set(); self.excluded_folders = set(); # Zurücksetzen
        self.default_category_name = "_Unsortiert"
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f: config_data = json.load(f)
        except FileNotFoundError:
            # Diese Zeile beginnt mit 12 Leerzeichen
            self.log(f"'{self.CONFIG_FILENAME}' nicht gefunden. Erstelle Standard...")
            # Diese Zeile beginnt mit 12 Leerzeichen
            config_data = self.create_default_config()
            # Diese Zeile beginnt mit 12 Leerzeichen
            if not config_data:
                # Diese Zeile beginnt mit 16 Leerzeichen
                self.log("FEHLER: Konnte keine Standardkonfiguration erstellen. Abbruch des Ladens.")
                # Diese Zeile beginnt mit 16 Leerzeichen
                return # Beendet die load_config Methode hier
        except json.JSONDecodeError as e: self.log(f"FEHLER Lesen JSON: {e}"); messagebox.showerror("Fehler", f"Fehler in '{self.CONFIG_FILENAME}': {e}\nDatei prüfen/löschen.", parent=self.master)
        except Exception as e: self.log(f"FEHLER Laden Config: {e}"); messagebox.showerror("Fehler", f"Fehler Laden Config:\n{e}", parent=self.master)

        if config_data and isinstance(config_data, dict):
            self.categories = config_data.get("Kategorien", {}); loaded_default = config_data.get("StandardKategorie", "_Unsortiert")
            self.default_category_name = loaded_default.strip() if isinstance(loaded_default, str) else "_Unsortiert"
            if not self.default_category_name: self.default_category_name = "_Unsortiert"; self.log("Warnung: StandardKategorie leer.")
            if isinstance(self.categories, dict):
                temp_ext_map = {};
                for category, extensions in self.categories.items():
                    if isinstance(extensions, list):
                        for ext in extensions:
                             if isinstance(ext, str) and ext.startswith('.'):
                                 ext_lower = ext.lower()
                                 if ext_lower in temp_ext_map: self.log(f"Warnung: Endung '{ext_lower}' mehrfach definiert ('{temp_ext_map[ext_lower]}', '{category}'). Verwende '{category}'.")
                                 temp_ext_map[ext_lower] = category
                             else: self.log(f"Warnung: Ignoriere ungültige Endung '{ext}' in Kat '{category}'.")
                    else: self.log(f"Warnung: Ungültiges Format für Extensions in Kat '{category}'.")
                self.extension_to_category = temp_ext_map
            else: self.log("FEHLER: 'Kategorien' kein Dictionary."); self.categories = {}

            excluded_list = config_data.get("AusgeschlosseneEndungen", [])
            if isinstance(excluded_list, list):
                valid_excluded = set();
                for ext in excluded_list:
                    if isinstance(ext, str) and ext.startswith('.'): valid_excluded.add(ext.lower())
                    else: self.log(f"Warnung: Ignoriere ungültige Ausschlusserweiterung '{ext}'.")
                self.excluded_extensions = valid_excluded
            else: self.log("Warnung: 'AusgeschlosseneEndungen' keine Liste."); self.excluded_extensions = set()

            excluded_folder_list = config_data.get("AusgeschlosseneOrdner", [])
            if isinstance(excluded_folder_list, list):
                valid_excluded_folders = set()
                for folder_name in excluded_folder_list:
                    if isinstance(folder_name, str) and folder_name.strip(): valid_excluded_folders.add(folder_name.strip().lower())
                    else: self.log(f"Warnung: Ignoriere ungültigen Ordnerausschluss '{folder_name}'.")
                self.excluded_folders = valid_excluded_folders
            else: self.log("Warnung: 'AusgeschlosseneOrdner' keine Liste."); self.excluded_folders = set()
        else:
             if config_data is not None: self.log("Konfigformat ungültig. Verwende Defaults.")
             self.categories = {}; self.extension_to_category = {}; self.default_category_name = "_Unsortiert"; self.excluded_extensions = set(); self.excluded_folders = set()

    # --- GUI Callbacks (Browse) ---
    def browse_source(self):
        """Öffnet Dialog zur Auswahl des Quellordners."""
        directory = filedialog.askdirectory(title="Quellordner auswählen", mustexist=True)
        if directory: self.source_dir.set(directory); self.log(f"Quellordner: {directory}")
    def browse_target(self):
        """Öffnet Dialog zur Auswahl des Zielordners."""
        directory = filedialog.askdirectory(title="Zielordner auswählen")
        if directory: self.target_dir.set(directory); self.log(f"Zielordner: {directory}")

    # --- Logging ---
    def log(self, message):
        """Fügt eine Nachricht mit Zeitstempel zum Log-Fenster hinzu."""
        try:
            if self.master.winfo_exists(): # Nur loggen, wenn Fenster existiert
                self.status_text.config(state='normal'); timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                self.status_text.insert(tk.END, f"[{timestamp}] {message}\n"); self.status_text.see(tk.END) # Auto-Scroll
                self.status_text.config(state='disabled')
        except tk.TclError: pass # Ignoriere Fehler bei Fensterzerstörung
        except Exception as e: print(f"Log-Fehler: {e}") # Andere Fehler ausgeben

    # --- Sortierlogik ---
    def start_sorting_thread(self):
        """Validiert Eingaben und startet den Sortiervorgang im Thread."""
        source = self.source_dir.get(); target = self.target_dir.get(); operation = self.operation_type.get()
        if not source or not os.path.isdir(source): messagebox.showerror("Fehler", "Gültigen Quellordner wählen.", parent=self.master); return
        if not target:
            default_target = os.path.join(source, "Sorted_Files")
            if messagebox.askyesno("Ziel fehlt", f"Kein Zielordner.\nStandard verwenden?\n\n'{default_target}'", parent=self.master):
                 self.target_dir.set(default_target); target = default_target
            else: return
        try:
            if not os.path.exists(target):
                if messagebox.askyesno("Ziel erstellen?", f"Zielordner existiert nicht:\n'{target}'\nErstellen?", icon='question', parent=self.master):
                    os.makedirs(target, exist_ok=True); self.log(f"Zielordner erstellt: {target}")
                else: return
            elif not os.path.isdir(target): messagebox.showerror("Fehler", f"Zielpfad kein Ordner:\n{target}", parent=self.master); return
        except OSError as e: messagebox.showerror("Fehler", f"Ziel nicht erstellt:\n{e}", parent=self.master); return
        try:
            source_abs = os.path.abspath(source); target_abs = os.path.abspath(target)
            if source_abs == target_abs or target_abs.startswith(source_abs + os.path.sep):
                 messagebox.showerror("Fehler", "Ziel darf nicht Quelle oder Unterordner sein.", parent=self.master); return
        except OSError as e: messagebox.showerror("Fehler", f"Pfadprüfung fehlgeschlagen:\n{e}", parent=self.master); return
        self.start_button.config(state="disabled"); self.progress_bar['value'] = 0
        self.log(f"Starte '{operation.upper()}' von '{source}' nach '{target}'...")
        thread = threading.Thread(target=self.sort_files, args=(source, target, operation), daemon=True); thread.start()

    def sort_files(self, source_dir, target_dir, operation):
        """Sortiert Dateien mit Typ-Unterordner-Logik und Ausschlüssen (Dateien + Ordner)."""
        processed_files_count = 0; skipped_count = 0; error_count = 0
        try:
            all_files = []; target_abs_dir = os.path.abspath(target_dir); self.log("Suche Dateien...")
            # WICHTIG: topdown=True für Modifikation von dirs
            for root, dirs, files in os.walk(source_dir, topdown=True):
                root_abs = os.path.abspath(root)
                # --- Unterordner ausschließen ---
                dirs[:] = [d for d in dirs if d.lower() not in self.excluded_folders]
                # --------------------------------
                if root_abs.startswith(target_abs_dir): continue
                for filename in files:
                    source_path = os.path.join(root, filename)
                    all_files.append(source_path)

            total_files = len(all_files)
            if total_files == 0: self.log("Keine Dateien zu verarbeiten gefunden."); self.master.after(0, self.show_completion_message, 0, 0, 0); return
            self.log(f"{total_files} Dateien gefunden. Starte Sortierung..."); self.progress_bar['maximum'] = total_files

            for i, source_path in enumerate(all_files): # Index für Fortschritt
                current_progress = i + 1
                if not self.master.winfo_exists(): self.log("Fenster geschlossen, Abbruch."); return
                filename = os.path.basename(source_path); _, file_extension = os.path.splitext(filename)
                file_extension_lower = file_extension.lower() if file_extension else ''

                # --- PRÜFUNG AUF AUSSCHLUSS (DATEIENDUNG) ---
                if file_extension_lower in self.excluded_extensions:
                    skipped_count += 1
                    self.master.after(0, self.update_progress, processed_files_count + skipped_count + error_count)
                    continue # Nächste Datei
                # ------------------------------------------

                category_name = self.extension_to_category.get(file_extension_lower, self.default_category_name)
                target_log_path = ""; category_target_dir = ""
                # *** LOGIK FÜR TYP-UNTERORDNER ***
                if category_name != self.default_category_name and file_extension_lower:
                    type_subfolder_name = file_extension_lower.lstrip('.')
                    if type_subfolder_name:
                         category_target_dir = os.path.join(target_dir, category_name, type_subfolder_name)
                         target_log_path = f"{category_name}{os.sep}{type_subfolder_name}"
                    else: category_target_dir = os.path.join(target_dir, category_name); target_log_path = category_name
                else: category_target_dir = os.path.join(target_dir, category_name); target_log_path = category_name
                # *********************************
                try:
                    if not os.path.isdir(category_target_dir): os.makedirs(category_target_dir, exist_ok=True)
                    target_path = os.path.join(category_target_dir, filename); counter = 1; original_target_path = target_path
                    while os.path.exists(target_path):
                        name, ext = os.path.splitext(filename); target_path = os.path.join(category_target_dir, f"{name}({counter}){ext}"); counter += 1
                    if original_target_path != target_path: self.log(f"Info: Ziel existiert. Neuer Name: '{os.path.basename(target_path)}' in '{target_log_path}'")
                    if operation == "copy": shutil.copy2(source_path, target_path)
                    elif operation == "move": shutil.move(source_path, target_path)
                    processed_files_count += 1
                except OSError as e: self.log(f"FEHLER bei '{filename}' -> '{target_log_path}': {e}"); error_count += 1
                except Exception as e: self.log(f"UNERWARTETER FEHLER bei '{filename}' -> '{target_log_path}': {e}"); error_count += 1
                finally:
                    self.master.after(0, self.update_progress, processed_files_count + skipped_count + error_count)

            self.master.after(0, self.show_completion_message, processed_files_count, skipped_count, error_count)

        except Exception as e:
            self.master.after(0, self.log, f"FATALER FEHLER im Sortier-Thread: {e}")
            self.master.after(0, messagebox.showerror, "Schwerer Fehler", f"Fehler im Sortierprozess:\n{e}", parent=self.master)
        finally: self.master.after(0, self.enable_start_button)

    # --- GUI Update Methoden ---
    def update_progress(self, value):
        """Aktualisiert den Wert des Fortschrittsbalkens."""
        try:
            if self.master.winfo_exists(): self.progress_bar['value'] = value
        except tk.TclError: pass
    def show_completion_message(self, success_count, skipped_count, error_count):
        """Zeigt die Abschlussmeldung im Log und als Popup an (berücksichtigt übersprungene)."""
        total_processed_or_skipped = success_count + skipped_count + error_count
        log_msg = ""; info_msg = ""; msg_type = "info"
        if total_processed_or_skipped == 0 and error_count == 0 :
            log_msg = "Vorgang beendet. Keine Dateien zum Verarbeiten gefunden."
            info_msg = "Keine Dateien im Quellordner gefunden (oder sie lagen bereits im Zielordner)."
        else:
            log_msg = f"Vorgang abgeschlossen. {success_count} Dateien erfolgreich verarbeitet."
            info_msg = f"Sortierung abgeschlossen!\n\nErfolgreich: {success_count}"
            if skipped_count > 0: log_msg += f" {skipped_count} übersprungen."; info_msg += f"\nÜbersprungen: {skipped_count}"
            if error_count > 0: log_msg += f" {error_count} FEHLER."; info_msg += f"\nFehler: {error_count}"; msg_type = "warning"
            else: msg_type = "info"
        self.log("--------------------"); self.log(log_msg)
        if msg_type == "info": messagebox.showinfo("Fertig", info_msg, parent=self.master)
        else: messagebox.showwarning("Fertig mit Fehlern/Warnungen", info_msg, parent=self.master)
        try:
            if self.master.winfo_exists(): self.progress_bar['value'] = 0
        except tk.TclError: pass
    def enable_start_button(self):
        """Aktiviert den Start-Button wieder."""
        try:
            if self.master.winfo_exists(): self.start_button.config(state="normal")
        except tk.TclError: pass

# -----------------------------------------------------------------------------
# Klasse CategoryEditor (MIT 3 TABS)
# -----------------------------------------------------------------------------
class CategoryEditor(tk.Toplevel):
    """
    Toplevel-Fenster zur Bearbeitung der Kategorien, ausgeschlossenen Endungen
    UND ausgeschlossenen Ordner mittels eines Tab-Layouts (Notebook).
    """
    def __init__(self, parent, config_file, current_categories, default_category,
                 current_excluded_extensions, current_excluded_folders): # Neuer Parameter
        """ Initialisiert den Editor mit 3 Tabs. """
        super().__init__(parent); self.transient(parent); self.parent = parent
        self.config_file = config_file; self.edited_categories = copy.deepcopy(current_categories)
        self.original_default_category = default_category
        self.edited_excluded_extensions = current_excluded_extensions.copy() # Set-Kopie
        self.edited_excluded_folders = current_excluded_folders.copy()      # Set-Kopie Ordner
        self.protocol("WM_DELETE_WINDOW", self.cancel_changes)
        self.title("Kategorien & Ausschlüsse bearbeiten"); self.geometry("700x550"); self.resizable(True, True); self.minsize(600, 450)

        self.notebook = ttk.Notebook(self)
        self.category_tab_frame = ttk.Frame(self.notebook, padding="10")
        self.exclusion_tab_frame = ttk.Frame(self.notebook, padding="10")
        self.folder_exclusion_tab_frame = ttk.Frame(self.notebook, padding="10") # NEU
        self.notebook.add(self.category_tab_frame, text='Kategorien')
        self.notebook.add(self.exclusion_tab_frame, text='Ausgeschl. Endungen')
        self.notebook.add(self.folder_exclusion_tab_frame, text='Ignorierte Ordner') # NEUER TAB
        self.notebook.pack(expand=True, fill=tk.BOTH, pady=(5, 5), padx=5) # Padding für Notebook
        button_frame = ttk.Frame(self); button_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        self.build_category_tab(); self.build_exclusion_tab(); self.build_folder_exclusion_tab() # NEU
        ttk.Button(button_frame, text="Speichern & Schließen", command=self.save_changes, style="Accent.TButton").pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Abbrechen", command=self.cancel_changes).pack(side=tk.RIGHT)
        style = ttk.Style(); style.configure("Accent.TButton", foreground="white", background="#0078D7")
        self.populate_category_list();
        if self.category_listbox.size() > 0: self.category_listbox.select_set(0); self.on_category_select(None)
        self.populate_exclusion_list(); self.populate_folder_exclusion_list() # NEU
        self.grab_set(); self.focus_set(); self.wait_window()

    def build_category_tab(self):
        """Erstellt die GUI-Elemente für den Kategorien-Tab."""
        frame = self.category_tab_frame; frame.columnconfigure(0, weight=1, minsize=200); frame.columnconfigure(1, weight=2); frame.rowconfigure(1, weight=1)
        ttk.Label(frame, text="Kategorien:").grid(row=0, column=0, sticky="w", pady=(0,2))
        cat_list_frame = ttk.Frame(frame); cat_list_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        cat_scrollbar = ttk.Scrollbar(cat_list_frame, orient=tk.VERTICAL)
        self.category_listbox = tk.Listbox(cat_list_frame, exportselection=False, yscrollcommand=cat_scrollbar.set)
        cat_scrollbar.config(command=self.category_listbox.yview); cat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.category_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); self.category_listbox.bind("<<ListboxSelect>>", self.on_category_select)
        cat_button_frame = ttk.Frame(frame); cat_button_frame.grid(row=2, column=0, sticky="ew", pady=(5,0))
        ttk.Button(cat_button_frame, text="Hinzufügen...", command=self.add_category).pack(side=tk.LEFT, padx=2)
        ttk.Button(cat_button_frame, text="Entfernen", command=self.remove_category).pack(side=tk.LEFT, padx=2)
        self.selected_category_label = ttk.Label(frame, text="Dateiendungen für: -")
        self.selected_category_label.grid(row=0, column=1, sticky="w", pady=(0,2))
        ext_list_frame = ttk.Frame(frame); ext_list_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        ext_scrollbar = ttk.Scrollbar(ext_list_frame, orient=tk.VERTICAL)
        self.extension_listbox = tk.Listbox(ext_list_frame, exportselection=False, yscrollcommand=ext_scrollbar.set)
        ext_scrollbar.config(command=self.extension_listbox.yview); ext_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.extension_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ext_input_frame = ttk.Frame(frame); ext_input_frame.grid(row=2, column=1, sticky="ew", pady=(5,0))
        self.extension_entry = ttk.Entry(ext_input_frame); self.extension_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.extension_entry.bind("<Return>", self.add_extension_event)
        ttk.Button(ext_input_frame, text="Hinzufügen", command=self.add_extension).pack(side=tk.LEFT, padx=2)
        ttk.Button(ext_input_frame, text="Entfernen", command=self.remove_extension).pack(side=tk.LEFT, padx=2)

    def build_exclusion_tab(self):
        """Erstellt die GUI-Elemente für den Ausschluss-Tab (Endungen)."""
        frame = self.exclusion_tab_frame; frame.columnconfigure(0, weight=1); frame.rowconfigure(1, weight=1)
        ttk.Label(frame, text="Ausgeschlossene Dateiendungen (werden ignoriert):").grid(row=0, column=0, sticky="w", pady=(0,2))
        excl_list_frame = ttk.Frame(frame); excl_list_frame.grid(row=1, column=0, sticky="nsew", pady=(0,5))
        excl_scrollbar = ttk.Scrollbar(excl_list_frame, orient=tk.VERTICAL)
        self.exclusion_listbox = tk.Listbox(excl_list_frame, exportselection=False, yscrollcommand=excl_scrollbar.set)
        excl_scrollbar.config(command=self.exclusion_listbox.yview); excl_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.exclusion_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        excl_input_frame = ttk.Frame(frame); excl_input_frame.grid(row=2, column=0, sticky="ew")
        self.exclusion_entry = ttk.Entry(excl_input_frame)
        self.exclusion_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.exclusion_entry.bind("<Return>", self.add_exclusion_event)
        ttk.Button(excl_input_frame, text="Hinzufügen", command=self.add_exclusion).pack(side=tk.LEFT, padx=2)
        ttk.Button(excl_input_frame, text="Entfernen", command=self.remove_exclusion).pack(side=tk.LEFT, padx=2)

    def build_folder_exclusion_tab(self):
        """Erstellt die GUI-Elemente für den Tab der ignorierten Ordner."""
        frame = self.folder_exclusion_tab_frame; frame.columnconfigure(0, weight=1); frame.rowconfigure(1, weight=1)
        ttk.Label(frame, text="Zu ignorierende Ordnernamen (Groß/Kleinschreibung egal):").grid(row=0, column=0, sticky="w", pady=(0,2))
        folder_excl_list_frame = ttk.Frame(frame); folder_excl_list_frame.grid(row=1, column=0, sticky="nsew", pady=(0,5))
        folder_excl_scrollbar = ttk.Scrollbar(folder_excl_list_frame, orient=tk.VERTICAL)
        self.folder_exclusion_listbox = tk.Listbox(folder_excl_list_frame, exportselection=False, yscrollcommand=folder_excl_scrollbar.set)
        folder_excl_scrollbar.config(command=self.folder_exclusion_listbox.yview); folder_excl_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.folder_exclusion_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        folder_excl_input_frame = ttk.Frame(frame); folder_excl_input_frame.grid(row=2, column=0, sticky="ew")
        self.folder_exclusion_entry = ttk.Entry(folder_excl_input_frame)
        self.folder_exclusion_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.folder_exclusion_entry.bind("<Return>", self.add_folder_exclusion_event)
        ttk.Button(folder_excl_input_frame, text="Hinzufügen", command=self.add_folder_exclusion).pack(side=tk.LEFT, padx=2)
        ttk.Button(folder_excl_input_frame, text="Entfernen", command=self.remove_folder_exclusion).pack(side=tk.LEFT, padx=2)

    # --- Methoden für die Listen (mit korrekter Einrückung) ---
    def populate_category_list(self):
        """Aktualisiert die Kategorien-Listbox (mit Indentation Fix)."""
        selection_index = self.category_listbox.curselection(); selected_value = self.category_listbox.get(selection_index[0]) if selection_index else None
        self.category_listbox.delete(0, tk.END); sorted_categories = sorted(self.edited_categories.keys()); new_selection_index = -1
        for i, category in enumerate(sorted_categories):
            self.category_listbox.insert(tk.END, category) # 12 spaces
            if category == selected_value:                 # 12 spaces
                new_selection_index = i                    # 16 spaces
        if new_selection_index != -1:                      # 8 spaces
            try:                                           # 12 spaces
                self.category_listbox.select_set(new_selection_index); self.category_listbox.activate(new_selection_index); self.category_listbox.see(new_selection_index) # 16 spaces
            except tk.TclError:                            # 12 spaces
                pass                                       # 16 spaces
        self.populate_extension_list()                     # 8 spaces
    def populate_extension_list(self):
        """Aktualisiert die Dateiendungs-Listbox (mit Indentation Fix)."""
        selection_index = self.extension_listbox.curselection(); selected_value = self.extension_listbox.get(selection_index[0]) if selection_index else None
        self.extension_listbox.delete(0, tk.END); selected_cat_indices = self.category_listbox.curselection()
        if selected_cat_indices:                           # 8 spaces
            selected_category = self.category_listbox.get(selected_cat_indices[0]) # 12 spaces
            self.selected_category_label.config(text=f"Dateiendungen für: {selected_category}") # 12 spaces
            extensions = self.edited_categories.get(selected_category, []); new_selection_index = -1 # 12 spaces
            for i, ext in enumerate(sorted(extensions)):   # 12 spaces
                self.extension_listbox.insert(tk.END, ext) # 16 spaces
                if ext == selected_value:                  # 16 spaces
                    new_selection_index = i                # 20 spaces
            if new_selection_index != -1:                  # 12 spaces
                try:                                       # 16 spaces
                    self.extension_listbox.select_set(new_selection_index); self.extension_listbox.activate(new_selection_index); self.extension_listbox.see(new_selection_index) # 20 spaces
                except tk.TclError:                        # 16 spaces
                    pass                                   # 20 spaces
        else:                                              # 8 spaces
             self.selected_category_label.config(text="Dateiendungen für: -") # 12 spaces
    def on_category_select(self, event): self.populate_extension_list()
    def populate_exclusion_list(self):
        """Aktualisiert die Listbox für ausgeschlossene Endungen."""
        selection_index = self.exclusion_listbox.curselection(); selected_value = self.exclusion_listbox.get(selection_index[0]) if selection_index else None
        self.exclusion_listbox.delete(0, tk.END); new_selection_index = -1
        sorted_exclusions = sorted(list(self.edited_excluded_extensions))
        for i, ext in enumerate(sorted_exclusions):
            self.exclusion_listbox.insert(tk.END, ext)
            if ext == selected_value: new_selection_index = i
        if new_selection_index != -1:
             try: self.exclusion_listbox.select_set(new_selection_index); self.exclusion_listbox.activate(new_selection_index); self.exclusion_listbox.see(new_selection_index)
             except tk.TclError: pass

    # --- Methoden für Ordner-Ausschluss-Liste ---
    def populate_folder_exclusion_list(self):
        """Aktualisiert die Listbox für ignorierte Ordner."""
        selection_index = self.folder_exclusion_listbox.curselection(); selected_value = self.folder_exclusion_listbox.get(selection_index[0]) if selection_index else None
        self.folder_exclusion_listbox.delete(0, tk.END); new_selection_index = -1
        sorted_folders = sorted(list(self.edited_excluded_folders))
        for i, folder_name in enumerate(sorted_folders):
            self.folder_exclusion_listbox.insert(tk.END, folder_name)
            if folder_name == selected_value: new_selection_index = i
        if new_selection_index != -1:
             try: self.folder_exclusion_listbox.select_set(new_selection_index); self.folder_exclusion_listbox.activate(new_selection_index); self.folder_exclusion_listbox.see(new_selection_index)
             except tk.TclError: pass
    def add_folder_exclusion_event(self, event): self.add_folder_exclusion()
    def add_folder_exclusion(self):
        """Fügt einen neuen Ordnernamen zur Ausschlussliste hinzu."""
        new_folder = self.folder_exclusion_entry.get().strip()
        if not new_folder: messagebox.showwarning("Leere Eingabe", "Ordnernamen eingeben.", parent=self); return
        if os.sep in new_folder or (os.altsep and os.altsep in new_folder): messagebox.showwarning("Ungültig", "Keinen Pfadtrenner verwenden.", parent=self); return
        new_folder_lower = new_folder.lower()
        if new_folder_lower not in self.edited_excluded_folders:
            self.edited_excluded_folders.add(new_folder_lower); self.populate_folder_exclusion_list(); self.folder_exclusion_entry.delete(0, tk.END)
            try:
                idx = list(self.folder_exclusion_listbox.get(0, tk.END)).index(new_folder_lower)
                self.folder_exclusion_listbox.select_clear(0, tk.END); self.folder_exclusion_listbox.select_set(idx)
                self.folder_exclusion_listbox.activate(idx); self.folder_exclusion_listbox.see(idx)
            except ValueError: pass
        else: messagebox.showinfo("Bereits vorhanden", f"Ordner '{new_folder}' ist bereits ausgeschlossen.", parent=self)
    def remove_folder_exclusion(self):
        """Entfernt den ausgewählten Ordnernamen aus der Ausschlussliste."""
        selected_indices = self.folder_exclusion_listbox.curselection()
        if not selected_indices: messagebox.showwarning("Keine Auswahl", "Zu entfernenden Ordnernamen auswählen.", parent=self); return
        selected_folder = self.folder_exclusion_listbox.get(selected_indices[0])
        if messagebox.askyesno("Bestätigung", f"Ordnername '{selected_folder}' aus Ausschlüssen entfernen?", parent=self):
            if selected_folder in self.edited_excluded_folders:
                self.edited_excluded_folders.remove(selected_folder); self.populate_folder_exclusion_list()

    # --- Methoden für Kategorie-Buttons (mit korrekter Einrückung) ---
    def add_category(self):
        """Fügt eine neue Kategorie hinzu (mit Indentation Fix)."""
        new_category = simpledialog.askstring("Neue Kategorie", "Namen eingeben:", parent=self)
        if new_category:                             # 8 spaces
            new_category = new_category.strip()      # 12 spaces
            if not new_category:                     # 12 spaces
                messagebox.showwarning("Ungültig", "Name leer.", parent=self) # 16 spaces
                return                               # 16 spaces
            if new_category in self.edited_categories: # 12 spaces
                messagebox.showwarning("Doppelt", "Existiert.", parent=self) # 16 spaces
            else:                                    # 12 spaces
                self.edited_categories[new_category] = [] # 16 spaces
                self.populate_category_list()         # 16 spaces
                try:                                  # 16 spaces
                    idx = list(self.category_listbox.get(0, tk.END)).index(new_category) # 20 spaces
                    self.category_listbox.select_clear(0, tk.END); self.category_listbox.select_set(idx) # 20 spaces
                    self.category_listbox.activate(idx); self.category_listbox.see(idx); self.on_category_select(None) # 20 spaces
                except ValueError:                    # 16 spaces
                    pass                              # 20 spaces
    def remove_category(self):
         """Entfernt die ausgewählte Kategorie."""
         selected_indices = self.category_listbox.curselection()
         if not selected_indices: messagebox.showwarning("Auswahl fehlt", "Kategorie auswählen.", parent=self); return
         selected_category = self.category_listbox.get(selected_indices[0])
         if messagebox.askyesno("Bestätigung", f"Kategorie '{selected_category}' entfernen?", icon='warning', parent=self):
             if selected_category in self.edited_categories: del self.edited_categories[selected_category]; self.populate_category_list()
    def add_extension_event(self, event): self.add_extension()
    def add_extension(self):
         """Fügt eine neue Extension hinzu."""
         selected_cat_indices = self.category_listbox.curselection()
         if not selected_cat_indices: messagebox.showwarning("Auswahl fehlt", "Kategorie auswählen.", parent=self); return
         selected_category = self.category_listbox.get(selected_cat_indices[0]); new_extension = self.extension_entry.get().strip().lower()
         if not new_extension: messagebox.showwarning("Leer", "Endung eingeben.", parent=self); return
         if not new_extension.startswith('.'): new_extension = '.' + new_extension
         if len(new_extension) < 2 : messagebox.showwarning("Ungültig", "Ungültige Endung.", parent=self); return
         if new_extension in self.edited_categories[selected_category]: messagebox.showwarning("Doppelt", "Endung existiert.", parent=self)
         else: self.edited_categories[selected_category].append(new_extension); self.populate_extension_list(); self.extension_entry.delete(0, tk.END)
    def remove_extension(self):
        """Entfernt die ausgewählte Extension."""
        selected_cat_indices = self.category_listbox.curselection(); selected_ext_indices = self.extension_listbox.curselection()
        if not selected_cat_indices or not selected_ext_indices: messagebox.showwarning("Auswahl fehlt", "Kategorie und Endung auswählen.", parent=self); return
        selected_category = self.category_listbox.get(selected_cat_indices[0]); selected_extension = self.extension_listbox.get(selected_ext_indices[0])
        if selected_extension in self.edited_categories[selected_category]:
            if messagebox.askyesno("Bestätigung", f"Endung '{selected_extension}' entfernen?", parent=self):
                 self.edited_categories[selected_category].remove(selected_extension); self.populate_extension_list()
    def add_exclusion_event(self, event): self.add_exclusion()
    def add_exclusion(self):
        """Fügt eine neue Endung zur Ausschlussliste hinzu."""
        new_exclusion = self.exclusion_entry.get().strip().lower()
        if not new_exclusion: messagebox.showwarning("Leere Eingabe", "Auszuschließende Endung eingeben (z.B. '.tmp').", parent=self); return
        if not new_exclusion.startswith('.'): new_exclusion = '.' + new_exclusion
        if len(new_exclusion) < 2: messagebox.showwarning("Ungültig", f"'{new_exclusion}' keine gültige Endung.", parent=self); return
        if new_exclusion not in self.edited_excluded_extensions:
            self.edited_excluded_extensions.add(new_exclusion); self.populate_exclusion_list(); self.exclusion_entry.delete(0, tk.END)
            try: # Neuen Eintrag auswählen
                idx = list(self.exclusion_listbox.get(0, tk.END)).index(new_exclusion)
                self.exclusion_listbox.select_clear(0, tk.END); self.exclusion_listbox.select_set(idx)
                self.exclusion_listbox.activate(idx); self.exclusion_listbox.see(idx)
            except ValueError: pass
        else: messagebox.showinfo("Bereits vorhanden", f"Endung '{new_exclusion}' ist bereits ausgeschlossen.", parent=self)
    def remove_exclusion(self):
        """Entfernt die ausgewählte Endung aus der Ausschlussliste."""
        selected_indices = self.exclusion_listbox.curselection()
        if not selected_indices: messagebox.showwarning("Keine Auswahl", "Auszuschließende Endung auswählen.", parent=self); return
        selected_exclusion = self.exclusion_listbox.get(selected_indices[0])
        if messagebox.askyesno("Bestätigung", f"Endung '{selected_exclusion}' aus Ausschlüssen entfernen?", parent=self):
            if selected_exclusion in self.edited_excluded_extensions:
                self.edited_excluded_extensions.remove(selected_exclusion); self.populate_exclusion_list()

    # --- Dialog Aktionen (ANGEPASST für BEIDE Ausschlüsse) ---
    def save_changes(self):
        """Speichert Kategorien, StandardKat, Ausschlüsse-Endungen UND Ausschlüsse-Ordner."""
        config_data_to_save = {
            "Kategorien": self.edited_categories,
            "StandardKategorie": self.original_default_category,
            "AusgeschlosseneEndungen": sorted(list(self.edited_excluded_extensions)),
            # NEU: Ausgeschlossene Ordner hinzufügen (als sortierte Liste)
            "AusgeschlosseneOrdner": sorted(list(self.edited_excluded_folders))
        }
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data_to_save, f, indent=4, ensure_ascii=False)
            self.destroy() # Fenster nach erfolgreichem Speichern schließen
        except OSError as e: messagebox.showerror("Speicherfehler", f"Konfiguration speichern fehlgeschlagen:\n{e}", parent=self)
        except Exception as e: messagebox.showerror("Fehler", f"Fehler beim Speichern:\n{e}", parent=self)

    def cancel_changes(self):
        """Schließt das Fenster ohne zu speichern."""
        self.destroy()


# -----------------------------------------------------------------------------
# Klasse InfoWindow (mit Logo)
# -----------------------------------------------------------------------------
class InfoWindow(tk.Toplevel):
    """ Zeigt Programminfo und Logo an. """
    def __init__(self, parent, current_year, app_version): # Nimmt Version entgegen
        super().__init__(parent); self.transient(parent); self.parent = parent
        self.title("Info"); self.resizable(False, False); self.protocol("WM_DELETE_WINDOW", self.destroy)
        info_frame = ttk.Frame(self, padding="15"); info_frame.pack(expand=True, fill=tk.BOTH)
        # Pfad zum Logo dynamisch ermitteln
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            logo_path = os.path.join(script_dir, 'logo.jpg')
        except NameError: # Falls __file__ nicht definiert ist (z.B. in interactive session)
            logo_path = 'logo.jpg'

        self.logo_image = None
        try:
            if not PIL_AVAILABLE: raise ImportError("Pillow (PIL) ist nicht installiert.")
            img = Image.open(logo_path); max_size = (200, 200); img.thumbnail(max_size, Image.Resampling.LANCZOS)
            self.logo_image = ImageTk.PhotoImage(img); logo_label = ttk.Label(info_frame, image=self.logo_image); logo_label.pack(pady=(0, 15))
        except FileNotFoundError: ttk.Label(info_frame, text=f"Logo '{logo_path}' nicht gefunden.").pack(pady=10)
        except ImportError as e: ttk.Label(info_frame, text=f"{e}\n(pip install Pillow)").pack(pady=10)
        except Exception as e: ttk.Label(info_frame, text=f"Fehler beim Laden des Logos:\n{e}", justify=tk.LEFT).pack(pady=10)

        # *** Änderung: Copyright Text ***
        copyright_text = f"Dateiexperte\nVersion {app_version}\n\nCopyright {current_year} @ Knut Wehr" # 'by' zu '@' geändert
        text_label = ttk.Label(info_frame, text=copyright_text, justify=tk.CENTER); text_label.pack(pady=(0, 15))
        ok_button = ttk.Button(info_frame, text="OK", command=self.destroy, style="Accent.TButton"); ok_button.pack(pady=(5, 0))
        ok_button.focus_set(); self.bind("<Return>", lambda event: self.destroy())
        self.update_idletasks(); parent_x = parent.winfo_rootx(); parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width(); parent_height = parent.winfo_height()
        dialog_width = self.winfo_reqwidth(); dialog_height = self.winfo_reqheight()
        x = max(0, parent_x + (parent_width // 2) - (dialog_width // 2)); y = max(0, parent_y + (parent_height // 2) - (dialog_height // 2))
        self.geometry(f'+{x}+{y}')
        self.grab_set(); self.wait_window()

# -----------------------------------------------------------------------------
# Klasse FileInfoDialog (mit Fix für Anzeige)
# -----------------------------------------------------------------------------
class FileInfoDialog(tk.Toplevel):
    """ Zeigt detaillierte Informationen zu einer Datei in einem modalen Fenster an. """
    def __init__(self, parent, info_dict):
        """ Initialisiert das Datei-Info-Fenster. """
        super().__init__(parent); self.transient(parent); self.parent = parent
        file_title = info_dict.get("Dateiname", "Datei"); self.title(f"Informationen für: {file_title}")
        self.resizable(False, False); self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.value_vars = []
        main_frame = ttk.Frame(self, padding="15"); main_frame.pack(expand=True, fill=tk.BOTH)
        info_frame = ttk.Frame(main_frame); info_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        info_frame.columnconfigure(1, weight=1)
        row_index = 0
        for key, value in info_dict.items():
            lbl_key = ttk.Label(info_frame, text=f"{key}:"); lbl_key.grid(row=row_index, column=0, sticky="nw", padx=(0, 10), pady=2)
            val_var = tk.StringVar(value=value); self.value_vars.append(val_var)
            entry_val = ttk.Entry(info_frame, textvariable=val_var, state="readonly", width=70); entry_val.grid(row=row_index, column=1, sticky="ew", pady=2)
            row_index += 1
        ok_button_frame = ttk.Frame(main_frame); ok_button_frame.pack(fill=tk.X, pady=(10, 0))
        ok_button = ttk.Button(ok_button_frame, text="OK", command=self.destroy, style="Accent.TButton"); ok_button.pack()
        ok_button.focus_set(); self.bind("<Return>", lambda event: self.destroy())
        self.update_idletasks(); parent_x = parent.winfo_rootx(); parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width(); parent_height = parent.winfo_height()
        dialog_width = self.winfo_reqwidth(); dialog_height = self.winfo_reqheight()
        x = max(0, parent_x + (parent_width // 2) - (dialog_width // 2)); y = max(0, parent_y + (parent_height // 2) - (dialog_height // 2))
        self.geometry(f'+{x}+{y}')
        self.grab_set(); self.wait_window()

# -----------------------------------------------------------------------------
# Hauptausführung: Startet die Anwendung
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk() # Erstellt das Hauptfenster
    # Optional: TTK Theme setzen
    # style = ttk.Style()
    # try:
    #     # Versuche ein verfügbares Theme zu verwenden
    #     if 'clam' in style.theme_names(): style.theme_use('clam')
    #     elif 'vista' in style.theme_names(): style.theme_use('vista') # Für Windows
    #     elif 'aqua' in style.theme_names(): style.theme_use('aqua') # Für macOS
    # except tk.TclError: pass # Ignoriere Fehler, wenn Theme nicht verfügbar
    app = FileSorterApp(root) # Erstellt die Anwendungsinstanz
    root.mainloop() # Startet die Tkinter-Event-Schleife