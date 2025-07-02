# -*- coding: utf-8 -*-
"""
Dateiexperte v1.11.2 (2025-04-21) - i18n Fix 2
Sortiert Dateien in einem Quellverzeichnis basierend auf Konfigurationsregeln
in ein Zielverzeichnis. Erstellt Kategorieordner und darin optional
Unterordner basierend auf der Dateiendung. Bietet Datei-Info-Funktion
und editierbare Ausschlussmöglichkeit für Dateiendungen und Ordnernamen.
Jetzt mehrsprachig über locales/*.json Dateien.

Benötigt: Pillow (`pip install Pillow`) für Logo-Anzeige.
           `logo.jpg` im Ordner `img/`.
           `sorter_config.json` (wird automatisch erstellt).
           `translator.py` mit Translator Klasse.
           `locales/` Ordner mit Sprachdateien (z.B. en.json, de.json).
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext, simpledialog
import os
import shutil
import threading
import json
import copy
import datetime
import locale # Für Systemspracheerkennung

# --- Pillow Import ---
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# --- Globale Fallback-Übersetzungsfunktion ---
def dummy_get_string(key, default=None, **kwargs):
    """Fallback-Funktion, wenn Translator nicht verfügbar ist."""
    text_to_format = default if default is not None else key
    if kwargs:
        try: return text_to_format.format(**kwargs)
        except KeyError: return text_to_format + " " + str(kwargs)
    return text_to_format

# --- Translator Import ---
try:
    from translator import Translator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    print("FEHLER: translator.py nicht gefunden oder enthält keine Translator-Klasse.")
    TRANSLATOR_AVAILABLE = False
    # _ wird später in __init__ auf dummy gesetzt

# -----------------------------------------------------------------------------
# Hauptanwendungsklasse
# -----------------------------------------------------------------------------
class FileSorterApp:
    """ Hauptklasse für die Dateiexperte-Anwendung mit GUI. """
    CONFIG_FILENAME = "sorter_config.json"
    APP_VERSION = "1.11.2" # Aktuelle Version

    def __init__(self, master):
        """ Initialisiert die Hauptanwendung. """
        self.master = master
        self.current_year = datetime.date.today().year

        # --- Translator initialisieren ---
        self._ = dummy_get_string # Standardmäßig Dummy
        self.translator = None
        if TRANSLATOR_AVAILABLE:
            #try: sys_lang = locale.getdefaultlocale()[0].split('_')[0].lower()
            try: sys_lang = locale.getlocale()[0].split('_')[0].lower()
            except: sys_lang = 'en'
            supported_langs = ['en', 'de', 'fr', 'es', 'pl']; initial_lang = sys_lang if sys_lang in supported_langs else 'en'
            try:
                self.translator = Translator(language_code=initial_lang, default_lang='en')
                self._ = self.translator.get_string
                print(f"Translator initialisiert mit Sprache: {self.translator.language}")
            except Exception as e_trans: print(f"FEHLER bei Translator-Initialisierung: {e_trans}"); messagebox.showerror("Übersetzungsfehler", f"Übersetzungsmodul nicht initialisiert:\n{e_trans}")
        else: self._ = dummy_get_string # Sicherstellen, dass _ den Dummy hat

        master.title(self._("AppTitle", default="Dateiexperte"))
        master.geometry("650x500"); master.minsize(600, 450)

        # --- Menüleiste ---
        menubar = tk.Menu(master); master.config(menu=menubar)
        edit_menu = tk.Menu(menubar, tearoff=0); menubar.add_cascade(label=self._("EditMenu", default="Bearbeiten"), menu=edit_menu); edit_menu.add_command(label=self._("FileInfoMenuItem", default="Datei-Info..."), command=self.show_file_info)
        settings_menu = tk.Menu(menubar, tearoff=0); menubar.add_cascade(label=self._("SettingsMenu", default="Einstellungen"), menu=settings_menu); settings_menu.add_command(label=self._("CategoriesMenuItem", default="Kategorien & Ausschlüsse..."), command=self.open_category_editor)
        info_menu = tk.Menu(menubar, tearoff=0); menubar.add_cascade(label=self._("InfoMenu", default="Info"), menu=info_menu); info_menu.add_command(label=self._("CopyrightMenuItem", default="Info / Copyright"), command=self.show_info_window)

        # --- Hauptframe & Status Text ---
        main_frame = ttk.Frame(master, padding="10"); main_frame.pack(fill=tk.BOTH, expand=True)
        self.status_text = scrolledtext.ScrolledText(main_frame, height=12, width=80, state='disabled', wrap=tk.WORD)

        # --- Konfiguration laden ---
        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.CONFIG_FILENAME)
        self.categories = {}; self.extension_to_category = {}; self.default_category_name = "_Unsortiert"; self.excluded_extensions = set(); self.excluded_folders = set()
        self.load_config()

        # --- Variablen für GUI ---
        self.source_dir = tk.StringVar(); self.target_dir = tk.StringVar(); self.operation_type = tk.StringVar(value="copy")

        # --- GUI Elemente Layout ---
        main_frame.columnconfigure(1, weight=1); main_frame.rowconfigure(6, weight=1)
        row_index = 0
        ttk.Label(main_frame, text=self._("SourceFolderLabel", default="Quellordner:")).grid(row=row_index, column=0, padx=5, pady=5, sticky="w")
        self.source_entry = ttk.Entry(main_frame, textvariable=self.source_dir, width=60); self.source_entry.grid(row=row_index, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(main_frame, text=self._("BrowseButton", default="Durchsuchen..."), command=self.browse_source).grid(row=row_index, column=2, padx=5, pady=5); row_index += 1
        ttk.Label(main_frame, text=self._("TargetFolderLabel", default="Zielordner:")).grid(row=row_index, column=0, padx=5, pady=5, sticky="w")
        self.target_entry = ttk.Entry(main_frame, textvariable=self.target_dir, width=60); self.target_entry.grid(row=row_index, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(main_frame, text=self._("BrowseButton", default="Durchsuchen..."), command=self.browse_target).grid(row=row_index, column=2, padx=5, pady=5); row_index += 1
        option_frame = ttk.Frame(main_frame); option_frame.grid(row=row_index, column=0, columnspan=3, padx=5, pady=5, sticky="w")
        ttk.Label(option_frame, text=self._("ActionButton", default="Aktion:")).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(option_frame, text=self._("CopyRadioButton", default="Kopieren"), variable=self.operation_type, value="copy").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(option_frame, text=self._("MoveRadioButton", default="Verschieben"), variable=self.operation_type, value="move").pack(side=tk.LEFT, padx=5); row_index += 1
        self.start_button = ttk.Button(main_frame, text=self._("StartButton", default="Sortieren starten"), command=self.start_sorting_thread, style="Accent.TButton")
        style = ttk.Style(); style.configure("Accent.TButton", foreground="white", background="#0078D7"); self.start_button.grid(row=row_index, column=0, columnspan=3, pady=15); row_index += 1
        self.progress_bar = ttk.Progressbar(main_frame, orient="horizontal", length=400, mode="determinate"); self.progress_bar.grid(row=row_index, column=0, columnspan=3, pady=5, padx=5, sticky="ew"); row_index += 1
        ttk.Label(main_frame, text=self._("StatusLabel", default="Status / Log:")).grid(row=row_index, column=0, columnspan=3, padx=5, pady=(10,0), sticky="w"); row_index += 1
        self.status_text.grid(row=row_index, column=0, columnspan=3, padx=5, pady=(0,10), sticky="nsew")

        # --- Initiales Logging ---
        self.log(self._("AppStartLog", default="App gestartet (v{version}). Konfig: {config}", version=self.APP_VERSION, config=self.config_file))
        if not PIL_AVAILABLE: self.log(self._("PillowWarningLog", default="WARNUNG: Pillow nicht gefunden."))
        self.log(self._("DefaultTargetLog", default="Standard-Ziel: '{target}'", target=self.default_category_name))
        self.log(self._("MappingInfoLog", default="{ext_count} Endungen gemappt.", ext_count=len(self.extension_to_category)))
        if self.excluded_extensions: self.log(self._("ExclusionInfoExtLog", default="{count} Endungen ausgeschlossen.", count=len(self.excluded_extensions)))
        if self.excluded_folders: self.log(self._("ExclusionInfoFolderLog", default="{count} Ordner ausgeschlossen.", count=len(self.excluded_folders)))

    # --- Menü-Callbacks ---
    def show_info_window(self):
        _ = self._
        if not PIL_AVAILABLE:
             messagebox.showwarning(_("PillowMissingWarningTitle", default="Pillow fehlt"), _("PillowMissingWarningMsg", default="Pillow fehlt..."), parent=self.master)
             messagebox.showinfo(_("InfoWindowTitle", default="Info"), _("AppInfoFallbackText", default="App Info...", version=self.APP_VERSION, year=self.current_year), parent=self.master)
             return
        info_window = InfoWindow(self.master, self.current_year, self.APP_VERSION, _)
    def open_category_editor(self):
        _ = self._
        editor_window = CategoryEditor(self.master, self.config_file, self.categories, self.default_category_name, self.excluded_extensions, self.excluded_folders, _)
        self.log(_("ConfigReloadLog", default="Lade Konfig nach Bearbeitung neu..."))
        self.load_config()
        self.log(_("ConfigReloadedLog", default="Konfig neu geladen.", ext_count=len(self.extension_to_category), excl_ext_count=len(self.excluded_extensions), excl_fld_count=len(self.excluded_folders)))
    # Innerhalb der FileSorterApp Klasse:

    def show_file_info(self):
        """Öffnet Dateiauswahldialog und zeigt Infos zur gewählten Datei an (Korrigiert)."""
        _ = self._ # Alias holen
        file_path = filedialog.askopenfilename(title=_("SelectFileInfoTitle", default="Datei für Info wählen"), parent=self.master)
        if not file_path: return

        try:
            stats = os.stat(file_path)
            info_to_display = {}
            # Verwende übersetzte Keys als Schlüssel im Dictionary
            key_filename = _("FileInfoLabelFilename", default="Dateiname")
            info_to_display[key_filename] = os.path.basename(file_path)
            full_path = os.path.abspath(file_path)
            info_to_display[_("FileInfoLabelFullPath", default="Voller Pfad")] = full_path
            info_to_display[_("FileInfoLabelDirectory", default="Verzeichnis")] = os.path.dirname(full_path)
            size_str = f"{self.format_size(stats.st_size)} ({stats.st_size:,} {_('BytesSuffix', default='Bytes')})"
            info_to_display[_("FileInfoLabelSize", default="Größe")] = size_str.replace(",", ".")
            dt_format = _("DateTimeFormat", default="%d.%m.%Y %H:%M:%S")
            created_suffix = _("FileInfoCreatedSuffix", default=" (Metadaten)")
            no_ext_str = _("FileInfoNoExtension", default="(Keine)")
            try: info_to_display[_("FileInfoLabelCreated", default="Erstellt")] = datetime.datetime.fromtimestamp(stats.st_ctime).strftime(dt_format) + created_suffix
            except OSError: info_to_display[_("FileInfoLabelCreated", default="Erstellt")] = "N/A"
            try: info_to_display[_("FileInfoLabelModified", default="Geändert")] = datetime.datetime.fromtimestamp(stats.st_mtime).strftime(dt_format)
            except OSError: info_to_display[_("FileInfoLabelModified", default="Geändert")] = "N/A"
            try: info_to_display[_("FileInfoLabelAccessed", default="Zugriff")] = datetime.datetime.fromtimestamp(stats.st_atime).strftime(dt_format)
            except OSError: info_to_display[_("FileInfoLabelAccessed", default="Zugriff")] = "N/A"

            # *** KORREKTUR HIER: Benutze anderen Namen statt '_' ***
            basename_part, extension = os.path.splitext(info_to_display[key_filename])
            # Jetzt ist _ immer noch die Funktion
            info_to_display[_("FileInfoLabelExtension", default="Dateiendung")] = extension if extension else no_ext_str

            FileInfoDialog(self.master, info_to_display, _) # Übergibt die (korrekte) _ Funktion

        except FileNotFoundError: messagebox.showerror(_("FileInfoErrorTitle", default="Fehler"), _("FileInfoNotFoundErrorMsg", default="Datei nicht gefunden:\n{path}", path=file_path), parent=self.master)
        except PermissionError: messagebox.showerror(_("FileInfoErrorTitle", default="Fehler"), _("FileInfoPermissionErrorMsg", default="Keine Rechte für:\n{path}", path=file_path), parent=self.master)
        except Exception as e:
            # Hier ist _ jetzt auch wieder die Funktion
            self.log(_("FileInfoErrorLog", default="Fehler bei Info für '{path}': {error}", path=file_path, error=e))
            messagebox.showerror(_("FileInfoErrorTitle", default="Fehler"), _("FileInfoGenericErrorMsg", default="Fehler beim Abrufen:\n{error}", error=e), parent=self.master)
    # --- Hilfsfunktion zur Größenformatierung ---
    def format_size(self, size_bytes):
        _ = self._
        if size_bytes < 0: return "N/A"
        if size_bytes < 1024: return f"{size_bytes} {_('BytesSuffix', default='Bytes')}"
        elif size_bytes < 1024**2: return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024**3: return f"{size_bytes / (1024**2):.2f} MB"
        else: return f"{size_bytes / (1024**3):.2f} GB"

    # --- Config Methoden ---
    def create_default_config(self):
        _ = self._
        default_config = {"Kategorien": {"Bilder": [".jpg",".png"],"Dokumente": [".pdf"]},"StandardKategorie": "_Unsortiert","AusgeschlosseneEndungen": [".tmp",".ini"],"AusgeschlosseneOrdner": ["temp",".git"]}
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f: json.dump(default_config, f, indent=4, ensure_ascii=False)
            self.log(_("ConfigFileCreatedLog", default="Standard-Config '{filename}' erstellt.", filename=self.CONFIG_FILENAME))
            return default_config
        except OSError as e: self.log(_("ConfigCreateErrorLog", default="FEHLER Erstellen Config: {error}", error=e)); messagebox.showerror(_("SaveErrorTitle", default="Speicherfehler"), _("ConfigCreateErrorMsg", default="Config nicht erstellt:\n{error}", error=e), parent=self.master); return None

    def load_config(self):
        """Lädt Konfig und baut Maps (mit Korrektur)."""
        _ = self._ # Alias holen
        config_data = None; self.categories = {}; self.extension_to_category = {}; self.excluded_extensions = set(); self.excluded_folders = set(); self.default_category_name = "_Unsortiert"
        try:
            # Diese Zeile beginnt mit 12 Leerzeichen
            with open(self.config_file, 'r', encoding='utf-8') as f:
                # Diese Zeile beginnt mit 16 Leerzeichen
                config_data = json.load(f)
        # Dieses except beginnt mit 8 Leerzeichen
        except FileNotFoundError:
            # Diese Zeilen beginnen mit 12 Leerzeichen
            self.log(_("ConfigNotFoundLog", default="'{filename}' nicht gefunden. Erstelle Standard...", filename=self.CONFIG_FILENAME))
            config_data = self.create_default_config()
            # Diese Zeile beginnt mit 12 Leerzeichen (KORRIGIERT)
            if not config_data:
                # Diese Zeilen beginnen mit 16 Leerzeichen
                self.log(_("ConfigCreateFailedLog", default="FEHLER: Konnte keine Standardkonfiguration erstellen. Abbruch des Ladens."))
                return # Beendet die load_config Methode hier
        # Dieses except beginnt mit 8 Leerzeichen
        except json.JSONDecodeError as e:
            self.log(_("ConfigJsonErrorLog", default="FEHLER Lesen JSON '{filename}': {error}", filename=self.CONFIG_FILENAME, error=e))
            messagebox.showerror(_("ConfigErrorTitle", default="Konfigurationsfehler"), _("ConfigJsonErrorMsg", default="Fehler in '{filename}': {error}\nDatei prüfen/löschen.", filename=self.CONFIG_FILENAME, error=e), parent=self.master)
            config_data = None
        # Dieses except beginnt mit 8 Leerzeichen
        except Exception as e:
             self.log(_("ConfigLoadGenericErrorLog", default="FEHLER Laden Config '{filename}': {error}", filename=self.CONFIG_FILENAME, error=e))
             messagebox.showerror(_("ConfigErrorTitle", default="Konfigurationsfehler"), _("ConfigLoadGenericErrorMsg", default="Fehler Laden Config:\n{error}", filename=self.CONFIG_FILENAME, error=e), parent=self.master)
             config_data = None

        # --- Konfiguration verarbeiten --- (Beginnt mit 8 Leerzeichen)
        if config_data and isinstance(config_data, dict):
            self.categories = config_data.get("Kategorien", {}); loaded_default = config_data.get("StandardKategorie", "_Unsortiert")
            self.default_category_name = loaded_default.strip() if isinstance(loaded_default, str) else "_Unsortiert"
            # *** KORREKTUR HIER ***
            if not self.default_category_name:
                self.default_category_name = "_Unsortiert"
                self.log(
                    _( "ConfigDefaultEmptyLog", # Key
                       default="Warnung: StandardKategorie leer, verwende '{def_val}'.", # Fallback-Text
                       def_val="_Unsortiert" # Wert für Platzhalter
                     )
                )
            # *** ENDE KORREKTUR ***
            if isinstance(self.categories, dict):
                temp_ext_map = {};
                for category, extensions in self.categories.items():
                    if isinstance(extensions, list):
                        for ext in extensions:
                             if isinstance(ext, str) and ext.startswith('.'):
                                 ext_lower = ext.lower()
                                 if ext_lower in temp_ext_map: self.log(_("DuplicateExtensionWarningLog", default="Warnung: Endung '{ext}' mehrfach def. ('{old_cat}', '{new_cat}'). Verwende '{new_cat}'.", ext=ext_lower, old_cat=temp_ext_map[ext_lower], new_cat=category))
                                 temp_ext_map[ext_lower] = category
                             else: self.log(_("InvalidExtensionWarningLog", default="Warnung: Ignoriere ungültige Endung '{ext}' in Kat '{category}'.", ext=ext, category=category))
                    else: self.log(_("ConfigExclusionsNotListErrorLog", default="Warnung: Ungültiges Format für '{key}'.", key=f"Extensions in Kat. '{category}'"))
                self.extension_to_category = temp_ext_map
            else: self.log(_("ConfigCategoriesNotDictErrorLog", default="FEHLER: 'Kategorien' kein Dictionary.")); self.categories = {}
            excluded_list = config_data.get("AusgeschlosseneEndungen", [])
            if isinstance(excluded_list, list):
                valid_excluded = set();
                for ext in excluded_list:
                    if isinstance(ext, str) and ext.startswith('.'): valid_excluded.add(ext.lower())
                    else: self.log(_("InvalidExclusionExtWarningLog", default="Warnung: Ignoriere ungültige Ausschlusserweiterung '{ext}'.", ext=ext))
                self.excluded_extensions = valid_excluded
            else: self.log(_("ConfigExclusionsNotListErrorLog", default="Warnung: '{key}' keine Liste.", key='AusgeschlosseneEndungen')); self.excluded_extensions = set()
            excluded_folder_list = config_data.get("AusgeschlosseneOrdner", [])
            if isinstance(excluded_folder_list, list):
                valid_excluded_folders = set()
                for folder_name in excluded_folder_list:
                    if isinstance(folder_name, str) and folder_name.strip(): valid_excluded_folders.add(folder_name.strip().lower())
                    else: self.log(_("InvalidExclusionFolderWarningLog", default="Warnung: Ignoriere ungültigen Ordnerausschluss '{folder}'.", folder=folder_name))
                self.excluded_folders = valid_excluded_folders
            else: self.log(_("ConfigExclusionsNotListErrorLog", default="Warnung: '{key}' keine Liste.", key='AusgeschlosseneOrdner')); self.excluded_folders = set()
        else:
             if config_data is not None: self.log(_("ConfigLoadErrorLog", default="Konfigformat ungültig. Verwende Defaults."))
             self.categories = {}; self.extension_to_category = {}; self.default_category_name = "_Unsortiert"; self.excluded_extensions = set(); self.excluded_folders = set()

    # --- GUI Callbacks (Browse) ---
    # ... (unverändert) ...
    def browse_source(self):
        _ = self._; directory = filedialog.askdirectory(title=_("BrowseSourceTitle", default="Quellordner auswählen"), mustexist=True, parent=self.master)
        if directory: self.source_dir.set(directory); self.log(_("SourceSelectedLog", default="Quellordner: {folder}", folder=directory))
    def browse_target(self):
        _ = self._; directory = filedialog.askdirectory(title=_("BrowseTargetTitle", default="Zielordner auswählen"), parent=self.master)
        if directory: self.target_dir.set(directory); self.log(_("TargetSelectedLog", default="Zielordner: {folder}", folder=directory))

    # --- Logging ---
    # ... (unverändert) ...
    def log(self, message):
        try:
            if self.master.winfo_exists(): self.status_text.config(state='normal'); timestamp = datetime.datetime.now().strftime("%H:%M:%S"); self.status_text.insert(tk.END, f"[{timestamp}] {message}\n"); self.status_text.see(tk.END); self.status_text.config(state='disabled')
        except tk.TclError: pass
        except Exception as e: print(f"Log-Fehler: {e}")

    # --- Sortierlogik ---
    # ... (unverändert) ...
    def start_sorting_thread(self):
        _ = self._; source = self.source_dir.get(); target = self.target_dir.get(); operation = self.operation_type.get()
        if not source or not os.path.isdir(source): messagebox.showerror(_("ErrorTitle"), _("InvalidSourceErrorMsg"), parent=self.master); return
        if not target:
            default_target = os.path.join(source, "Sorted_Files")
            if messagebox.askyesno(_("TargetMissingTitle"), _("TargetMissingMsg", path=default_target), parent=self.master): self.target_dir.set(default_target); target = default_target
            else: return
        try:
            if not os.path.exists(target):
                if messagebox.askyesno(_("TargetCreateTitle"), _("TargetCreateMsg", path=target), icon='question', parent=self.master): os.makedirs(target, exist_ok=True); self.log(_("TargetCreatedLog", folder=target))
                else: return
            elif not os.path.isdir(target): messagebox.showerror(_("ErrorTitle"), _("TargetNotDirErrorMsg", path=target), parent=self.master); return
        except OSError as e: messagebox.showerror(_("ErrorTitle"), _("TargetCreateErrorMsg", error=e), parent=self.master); return
        try:
            source_abs = os.path.abspath(source); target_abs = os.path.abspath(target)
            if source_abs == target_abs or target_abs.startswith(source_abs + os.path.sep): messagebox.showerror(_("ErrorTitle"), _("TargetIsSourceErrorMsg"), parent=self.master); return
        except OSError as e: messagebox.showerror(_("ErrorTitle"), _("PathCheckErrorMsg", error=e), parent=self.master); return
        self.start_button.config(state="disabled"); self.progress_bar['value'] = 0
        self.log(_("StartLog", action=operation.upper(), source=source, target=target))
        thread = threading.Thread(target=self.sort_files, args=(source, target, operation), daemon=True); thread.start()
    def sort_files(self, source_dir, target_dir, operation):
        _ = self._; processed_files_count = 0; skipped_count = 0; error_count = 0
        try:
            all_files = []; target_abs_dir = os.path.abspath(target_dir); self.log(_("SearchingFilesLog"))
            for root, dirs, files in os.walk(source_dir, topdown=True):
                root_abs = os.path.abspath(root); dirs[:] = [d for d in dirs if d.lower() not in self.excluded_folders]
                if root_abs.startswith(target_abs_dir): continue
                for filename in files: all_files.append(os.path.join(root, filename))
            total_files = len(all_files)
            if total_files == 0: self.log(_("NoFilesFoundLog")); self.master.after(0, self.show_completion_message, 0, 0, 0); return
            self.log(_("FilesFoundLog", count=total_files)); self.progress_bar['maximum'] = total_files
            for i, source_path in enumerate(all_files):
                current_progress = i + 1;
                if not self.master.winfo_exists(): self.log("Fenster geschlossen, Abbruch."); return
                filename = os.path.basename(source_path); _, file_extension = os.path.splitext(filename)
                file_extension_lower = file_extension.lower() if file_extension else ''
                if file_extension_lower in self.excluded_extensions: skipped_count += 1; self.master.after(0, self.update_progress, processed_files_count + skipped_count + error_count); continue
                category_name = self.extension_to_category.get(file_extension_lower, self.default_category_name)
                target_log_path = ""; category_target_dir = ""
                if category_name != self.default_category_name and file_extension_lower:
                    type_subfolder_name = file_extension_lower.lstrip('.')
                    if type_subfolder_name: category_target_dir = os.path.join(target_dir, category_name, type_subfolder_name); target_log_path = f"{category_name}{os.sep}{type_subfolder_name}"
                    else: category_target_dir = os.path.join(target_dir, category_name); target_log_path = category_name
                else: category_target_dir = os.path.join(target_dir, category_name); target_log_path = category_name
                try:
                    if not os.path.isdir(category_target_dir): os.makedirs(category_target_dir, exist_ok=True)
                    target_path = os.path.join(category_target_dir, filename); counter = 1; original_target_path = target_path
                    while os.path.exists(target_path): name, ext = os.path.splitext(filename); target_path = os.path.join(category_target_dir, f"{name}({counter}){ext}"); counter += 1
                    if original_target_path != target_path: self.log(_("TargetExistsLog", new_name=os.path.basename(target_path), target_path=target_log_path))
                    if operation == "copy": shutil.copy2(source_path, target_path)
                    elif operation == "move": shutil.move(source_path, target_path)
                    processed_files_count += 1
                except OSError as e: self.log(_("CopyErrorLog", filename=filename, target_path=target_log_path, error=e)); error_count += 1
                except Exception as e: self.log(_("UnexpectedErrorLog", filename=filename, target_path=target_log_path, error=e)); error_count += 1
                finally: self.master.after(0, self.update_progress, processed_files_count + skipped_count + error_count)
            self.master.after(0, self.show_completion_message, processed_files_count, skipped_count, error_count)
        except Exception as e:
            self.master.after(0, self.log, _("FatalThreadErrorLog", error=e))
            self.master.after(0, messagebox.showerror, _("FatalErrorTitle"), _("FatalThreadErrorMsg", error=e), parent=self.master)
        finally: self.master.after(0, self.enable_start_button)

    # --- GUI Update Methoden ---
    # ... (unverändert, verwenden self._) ...
    def update_progress(self, value):
        try:
            if self.master.winfo_exists(): self.progress_bar['value'] = value
        except tk.TclError: pass
    def show_completion_message(self, success_count, skipped_count, error_count):
        _ = self._; total_processed_or_skipped = success_count + skipped_count + error_count
        log_msg = ""; info_msg = ""; msg_type = "info"; title = _("CompletionTitleSuccess", default="Fertig")
        if total_processed_or_skipped == 0 and error_count == 0 :
            log_msg = _("LogCompletionNoFiles", default="Vorgang beendet. Keine Dateien zum Verarbeiten gefunden.")
            info_msg = _("MsgCompletionNoFiles", default="Keine Dateien im Quellordner gefunden.")
        else:
            log_msg = _("LogCompletion", default="Vorgang abgeschlossen. {success} Dateien erfolgreich verarbeitet.", success=success_count)
            info_msg = _("CompletionMsgSuccess", default="Sortierung abgeschlossen!\n\nErfolgreich: {success}", success=success_count)
            if skipped_count > 0: log_msg += _("LogCompletionSkipped", default=" {skipped} übersprungen.", skipped=skipped_count); info_msg += _("CompletionMsgSkipped", default="\nÜbersprungen: {skipped}", skipped=skipped_count)
            if error_count > 0: log_msg += _("LogCompletionError", default=" {errors} FEHLER.", errors=error_count); info_msg += _("CompletionMsgError", default="\nFehler: {errors}", errors=error_count); msg_type = "warning"; title = _("CompletionTitleWarning", default="Fertig mit Fehlern/Warnungen")
            else: msg_type = "info"
        self.log(_("LogSeparator", default="--------------------")); self.log(log_msg)
        if msg_type == "info": messagebox.showinfo(title, info_msg, parent=self.master)
        else: messagebox.showwarning(title, info_msg, parent=self.master)
        try:
            if self.master.winfo_exists(): self.progress_bar['value'] = 0
        except tk.TclError: pass
    def enable_start_button(self):
        try:
            if self.master.winfo_exists(): self.start_button.config(state="normal")
        except tk.TclError: pass


# -----------------------------------------------------------------------------
# Klasse CategoryEditor (MIT 3 TABS und Übersetzungen)
# -----------------------------------------------------------------------------
# (Diese Klasse bleibt unverändert zur letzten Version v1.10)
class CategoryEditor(tk.Toplevel):
    def __init__(self, parent, config_file, current_categories, default_category,
                 current_excluded_extensions, current_excluded_folders, translator_func): # Translator func übergeben
        super().__init__(parent); self.transient(parent); self.parent = parent
        self._ = translator_func # Lokalen Alias setzen
        self.config_file = config_file; self.edited_categories = copy.deepcopy(current_categories)
        self.original_default_category = default_category
        self.edited_excluded_extensions = current_excluded_extensions.copy()
        self.edited_excluded_folders = current_excluded_folders.copy()
        self.protocol("WM_DELETE_WINDOW", self.cancel_changes)
        self.title(self._("CategoryEditorTitle", default="Kategorien & Ausschlüsse bearbeiten")); self.geometry("700x550"); self.resizable(True, True); self.minsize(600, 450)
        self.notebook = ttk.Notebook(self)
        self.category_tab_frame = ttk.Frame(self.notebook, padding="10")
        self.exclusion_tab_frame = ttk.Frame(self.notebook, padding="10")
        self.folder_exclusion_tab_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.category_tab_frame, text=self._("CategoriesTab", default="Kategorien"))
        self.notebook.add(self.exclusion_tab_frame, text=self._("ExclusionsTab", default="Ausgeschl. Endungen"))
        self.notebook.add(self.folder_exclusion_tab_frame, text=self._("FoldersTab", default="Ignorierte Ordner"))
        self.notebook.pack(expand=True, fill=tk.BOTH, pady=(5, 5), padx=5)
        button_frame = ttk.Frame(self); button_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        self.build_category_tab(); self.build_exclusion_tab(); self.build_folder_exclusion_tab()
        ttk.Button(button_frame, text=self._("SaveButton", default="Speichern & Schließen"), command=self.save_changes, style="Accent.TButton").pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text=self._("CancelButton", default="Abbrechen"), command=self.cancel_changes).pack(side=tk.RIGHT)
        style = ttk.Style(); style.configure("Accent.TButton", foreground="white", background="#0078D7")
        self.populate_category_list();
        if self.category_listbox.size() > 0: self.category_listbox.select_set(0); self.on_category_select(None)
        self.populate_exclusion_list(); self.populate_folder_exclusion_list()
        self.grab_set(); self.focus_set(); self.wait_window()
    def build_category_tab(self):
        frame = self.category_tab_frame; _ = self._
        frame.columnconfigure(0, weight=1, minsize=200); frame.columnconfigure(1, weight=2); frame.rowconfigure(1, weight=1)
        ttk.Label(frame, text=_("CategoryListLabel", default="Kategorien:")).grid(row=0, column=0, sticky="w", pady=(0,2))
        cat_list_frame = ttk.Frame(frame); cat_list_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        cat_scrollbar = ttk.Scrollbar(cat_list_frame, orient=tk.VERTICAL)
        self.category_listbox = tk.Listbox(cat_list_frame, exportselection=False, yscrollcommand=cat_scrollbar.set)
        cat_scrollbar.config(command=self.category_listbox.yview); cat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.category_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); self.category_listbox.bind("<<ListboxSelect>>", self.on_category_select)
        cat_button_frame = ttk.Frame(frame); cat_button_frame.grid(row=2, column=0, sticky="ew", pady=(5,0))
        ttk.Button(cat_button_frame, text=_("AddButton", default="Hinzufügen..."), command=self.add_category).pack(side=tk.LEFT, padx=2)
        ttk.Button(cat_button_frame, text=_("RemoveButton", default="Entfernen"), command=self.remove_category).pack(side=tk.LEFT, padx=2)
        self.selected_category_label = ttk.Label(frame, text=_("ExtensionListLabel", default="Endungen für: {category}", category='-'))
        self.selected_category_label.grid(row=0, column=1, sticky="w", pady=(0,2))
        ext_list_frame = ttk.Frame(frame); ext_list_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        ext_scrollbar = ttk.Scrollbar(ext_list_frame, orient=tk.VERTICAL)
        self.extension_listbox = tk.Listbox(ext_list_frame, exportselection=False, yscrollcommand=ext_scrollbar.set)
        ext_scrollbar.config(command=self.extension_listbox.yview); ext_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.extension_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ext_input_frame = ttk.Frame(frame); ext_input_frame.grid(row=2, column=1, sticky="ew", pady=(5,0))
        self.extension_entry = ttk.Entry(ext_input_frame); self.extension_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.extension_entry.bind("<Return>", self.add_extension_event)
        ttk.Button(ext_input_frame, text=_("AddButtonShort", default="Add"), command=self.add_extension).pack(side=tk.LEFT, padx=2)
        ttk.Button(ext_input_frame, text=_("RemoveButton"), command=self.remove_extension).pack(side=tk.LEFT, padx=2)
    def build_exclusion_tab(self):
        frame = self.exclusion_tab_frame; _ = self._
        frame.columnconfigure(0, weight=1); frame.rowconfigure(1, weight=1)
        ttk.Label(frame, text=_("ExclusionListLabel", default="Ausgeschl. Endungen:")).grid(row=0, column=0, sticky="w", pady=(0,2))
        excl_list_frame = ttk.Frame(frame); excl_list_frame.grid(row=1, column=0, sticky="nsew", pady=(0,5))
        excl_scrollbar = ttk.Scrollbar(excl_list_frame, orient=tk.VERTICAL)
        self.exclusion_listbox = tk.Listbox(excl_list_frame, exportselection=False, yscrollcommand=excl_scrollbar.set)
        excl_scrollbar.config(command=self.exclusion_listbox.yview); excl_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.exclusion_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        excl_input_frame = ttk.Frame(frame); excl_input_frame.grid(row=2, column=0, sticky="ew")
        self.exclusion_entry = ttk.Entry(excl_input_frame)
        self.exclusion_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.exclusion_entry.bind("<Return>", self.add_exclusion_event)
        ttk.Button(excl_input_frame, text=_("AddButtonShort", default="Add"), command=self.add_exclusion).pack(side=tk.LEFT, padx=2)
        ttk.Button(excl_input_frame, text=_("RemoveButton"), command=self.remove_exclusion).pack(side=tk.LEFT, padx=2)
    def build_folder_exclusion_tab(self):
        frame = self.folder_exclusion_tab_frame; _ = self._
        frame.columnconfigure(0, weight=1); frame.rowconfigure(1, weight=1)
        ttk.Label(frame, text=_("FolderExclusionListLabel", default="Ignorierte Ordner:")).grid(row=0, column=0, sticky="w", pady=(0,2))
        folder_excl_list_frame = ttk.Frame(frame); folder_excl_list_frame.grid(row=1, column=0, sticky="nsew", pady=(0,5))
        folder_excl_scrollbar = ttk.Scrollbar(folder_excl_list_frame, orient=tk.VERTICAL)
        self.folder_exclusion_listbox = tk.Listbox(folder_excl_list_frame, exportselection=False, yscrollcommand=folder_excl_scrollbar.set)
        folder_excl_scrollbar.config(command=self.folder_exclusion_listbox.yview); folder_excl_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.folder_exclusion_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        folder_excl_input_frame = ttk.Frame(frame); folder_excl_input_frame.grid(row=2, column=0, sticky="ew")
        self.folder_exclusion_entry = ttk.Entry(folder_excl_input_frame)
        self.folder_exclusion_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.folder_exclusion_entry.bind("<Return>", self.add_folder_exclusion_event)
        ttk.Button(folder_excl_input_frame, text=_("AddButtonShort", default="Add"), command=self.add_folder_exclusion).pack(side=tk.LEFT, padx=2)
        ttk.Button(folder_excl_input_frame, text=_("RemoveButton"), command=self.remove_folder_exclusion).pack(side=tk.LEFT, padx=2)
    def populate_category_list(self):
        selection_index = self.category_listbox.curselection(); selected_value = self.category_listbox.get(selection_index[0]) if selection_index else None
        self.category_listbox.delete(0, tk.END); sorted_categories = sorted(self.edited_categories.keys()); new_selection_index = -1
        for i, category in enumerate(sorted_categories):
            self.category_listbox.insert(tk.END, category)
            if category == selected_value:
                new_selection_index = i
        if new_selection_index != -1:
            try: self.category_listbox.select_set(new_selection_index); self.category_listbox.activate(new_selection_index); self.category_listbox.see(new_selection_index)
            except tk.TclError: pass
        self.populate_extension_list()
    def populate_extension_list(self):
        _ = self._
        selection_index = self.extension_listbox.curselection(); selected_value = self.extension_listbox.get(selection_index[0]) if selection_index else None
        self.extension_listbox.delete(0, tk.END); selected_cat_indices = self.category_listbox.curselection()
        if selected_cat_indices:
            selected_category = self.category_listbox.get(selected_cat_indices[0])
            self.selected_category_label.config(text=_("ExtensionListLabel", default="Endungen für: {category}", category=selected_category))
            extensions = self.edited_categories.get(selected_category, []); new_selection_index = -1
            for i, ext in enumerate(sorted(extensions)):
                self.extension_listbox.insert(tk.END, ext)
                if ext == selected_value:
                    new_selection_index = i
            if new_selection_index != -1:
                try: self.extension_listbox.select_set(new_selection_index); self.extension_listbox.activate(new_selection_index); self.extension_listbox.see(new_selection_index)
                except tk.TclError: pass
        else: self.selected_category_label.config(text=_("ExtensionListLabel", default="Endungen für: {category}", category='-'))
    def on_category_select(self, event): self.populate_extension_list()
    def populate_exclusion_list(self):
        selection_index = self.exclusion_listbox.curselection(); selected_value = self.exclusion_listbox.get(selection_index[0]) if selection_index else None
        self.exclusion_listbox.delete(0, tk.END); new_selection_index = -1
        sorted_exclusions = sorted(list(self.edited_excluded_extensions))
        for i, ext in enumerate(sorted_exclusions):
            self.exclusion_listbox.insert(tk.END, ext)
            if ext == selected_value: new_selection_index = i
        if new_selection_index != -1:
             try: self.exclusion_listbox.select_set(new_selection_index); self.exclusion_listbox.activate(new_selection_index); self.exclusion_listbox.see(new_selection_index)
             except tk.TclError: pass
    def populate_folder_exclusion_list(self):
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
        _ = self._; new_folder = self.folder_exclusion_entry.get().strip()
        if not new_folder: messagebox.showwarning(_("EmptyInputWarningTitle"), _("EmptyInputFolderMsg"), parent=self); return
        if os.sep in new_folder or (os.altsep and os.altsep in new_folder): messagebox.showwarning(_("InvalidNameWarningTitle"), _("InvalidFolderNameWarningMsg"), parent=self); return
        new_folder_lower = new_folder.lower()
        if new_folder_lower not in self.edited_excluded_folders:
            self.edited_excluded_folders.add(new_folder_lower); self.populate_folder_exclusion_list(); self.folder_exclusion_entry.delete(0, tk.END)
            try: idx = list(self.folder_exclusion_listbox.get(0, tk.END)).index(new_folder_lower); self.folder_exclusion_listbox.select_clear(0, tk.END); self.folder_exclusion_listbox.select_set(idx); self.folder_exclusion_listbox.activate(idx); self.folder_exclusion_listbox.see(idx)
            except ValueError: pass
        else: messagebox.showinfo(_("DuplicateNameWarningTitle"), _("AlreadyExcludedFolderMsg", folder=new_folder), parent=self)
    def remove_folder_exclusion(self):
        _ = self._; selected_indices = self.folder_exclusion_listbox.curselection()
        if not selected_indices: messagebox.showwarning(_("NoSelectionWarningTitle"), _("NoFolderExclusionSelectedMsg"), parent=self); return
        selected_folder = self.folder_exclusion_listbox.get(selected_indices[0])
        if messagebox.askyesno(_("ConfirmRemoveTitle"), _("ConfirmRemoveFolderExclusionMsg", folder=selected_folder), parent=self):
            if selected_folder in self.edited_excluded_folders: self.edited_excluded_folders.remove(selected_folder); self.populate_folder_exclusion_list()
    def add_category(self):
        """Fügt eine neue Kategorie hinzu (mit sauberer Formatierung)."""
        # Diese Zeile beginnt mit 8 Leerzeichen
        new_category = simpledialog.askstring(self._("NewCategoryTitle", default="Neue Kategorie"), self._("NewCategoryPrompt", default="Namen eingeben:"), parent=self)

        # Diese Zeile beginnt mit 8 Leerzeichen
        if new_category:
            # --- Block beginnt hier, 12 Leerzeichen ---
            new_category = new_category.strip() # Jetzt auf eigener Zeile

            # Nächste Abfrage, auch 12 Leerzeichen
            if not new_category:
                # Inhalt beginnt mit 16 Leerzeichen
                messagebox.showwarning(self._("InvalidNameWarningTitle", default="Ungültiger Name"), self._("InvalidNameWarningMsg", default="Name leer."), parent=self)
                return

            # Nächste Abfrage, auch 12 Leerzeichen
            if new_category in self.edited_categories:
                # Inhalt beginnt mit 16 Leerzeichen
                messagebox.showwarning(self._("DuplicateNameWarningTitle", default="Doppelter Name"), self._("DuplicateNameWarningMsg", default="Existiert.", name=new_category), parent=self)
            else: # else gehört zum inneren if - beginnt mit 12 Leerzeichen
                # Inhalt beginnt mit 16 Leerzeichen
                self.edited_categories[new_category] = []
                self.populate_category_list()
                try: # try beginnt mit 16 Leerzeichen
                    # Inhalt beginnt mit 20 Leerzeichen
                    idx = list(self.category_listbox.get(0, tk.END)).index(new_category)
                    self.category_listbox.select_clear(0, tk.END)
                    self.category_listbox.select_set(idx)
                    self.category_listbox.activate(idx)
                    self.category_listbox.see(idx)
                    self.on_category_select(None)
                except ValueError: # except gehört zum try, 16 Leerzeichen
                    # Inhalt beginnt mit 20 Leerzeichen
                    pass # Fehler ignorieren
    def remove_category(self):
         _ = self._; selected_indices = self.category_listbox.curselection()
         if not selected_indices: messagebox.showwarning(_("NoSelectionWarningTitle"), _("NoCategorySelectedMsg"), parent=self); return
         selected_category = self.category_listbox.get(selected_indices[0])
         if messagebox.askyesno(_("ConfirmRemoveTitle"), _("ConfirmRemoveCategoryMsg", category=selected_category), icon='warning', parent=self):
             if selected_category in self.edited_categories: del self.edited_categories[selected_category]; self.populate_category_list()
    def add_extension_event(self, event): self.add_extension()
    def add_extension(self):
         _ = self._; selected_cat_indices = self.category_listbox.curselection()
         if not selected_cat_indices: messagebox.showwarning(_("NoSelectionWarningTitle"), _("NoCategorySelectedMsg"), parent=self); return
         selected_category = self.category_listbox.get(selected_cat_indices[0]); new_extension = self.extension_entry.get().strip().lower()
         if not new_extension: messagebox.showwarning(_("EmptyInputWarningTitle"), _("EmptyInputExtensionMsg"), parent=self); return
         if not new_extension.startswith('.'): new_extension = '.' + new_extension
         if len(new_extension) < 2 : messagebox.showwarning(_("InvalidExtensionWarningTitle"), _("InvalidExtensionWarningMsg", ext=new_extension), parent=self); return
         if new_extension in self.edited_categories[selected_category]: messagebox.showwarning(_("DuplicateNameWarningTitle"), _("DuplicateExtensionExistsInCategoryMsg", default="Endung '{ext}' existiert bereits in Kat. '{category}'.", ext=new_extension, category=selected_category), parent=self)
         else: self.edited_categories[selected_category].append(new_extension); self.populate_extension_list(); self.extension_entry.delete(0, tk.END)
    def remove_extension(self):
        _ = self._; selected_cat_indices = self.category_listbox.curselection(); selected_ext_indices = self.extension_listbox.curselection()
        if not selected_cat_indices or not selected_ext_indices: messagebox.showwarning(_("NoSelectionWarningTitle"), _("NoCatOrExtSelectedMsg", default="Kategorie und Endung auswählen."), parent=self); return
        selected_category = self.category_listbox.get(selected_cat_indices[0]); selected_extension = self.extension_listbox.get(selected_ext_indices[0])
        if selected_extension in self.edited_categories[selected_category]:
            if messagebox.askyesno(_("ConfirmRemoveTitle"), _("ConfirmRemoveExtensionMsg", ext=selected_extension, category=selected_category), parent=self):
                 self.edited_categories[selected_category].remove(selected_extension); self.populate_extension_list()
    def add_exclusion_event(self, event): self.add_exclusion()
    def add_exclusion(self):
        _ = self._; new_exclusion = self.exclusion_entry.get().strip().lower()
        if not new_exclusion: messagebox.showwarning(_("EmptyInputWarningTitle"), _("EmptyInputExclusionMsg"), parent=self); return
        if not new_exclusion.startswith('.'): new_exclusion = '.' + new_exclusion
        if len(new_exclusion) < 2: messagebox.showwarning(_("InvalidExtensionWarningTitle"), _("InvalidExtensionWarningMsg", ext=new_exclusion), parent=self); return
        if new_exclusion not in self.edited_excluded_extensions:
            self.edited_excluded_extensions.add(new_exclusion); self.populate_exclusion_list(); self.exclusion_entry.delete(0, tk.END)
            try: idx = list(self.exclusion_listbox.get(0, tk.END)).index(new_exclusion); self.exclusion_listbox.select_clear(0, tk.END); self.exclusion_listbox.select_set(idx); self.exclusion_listbox.activate(idx); self.exclusion_listbox.see(idx)
            except ValueError: pass
        else: messagebox.showinfo(_("DuplicateNameWarningTitle"), _("AlreadyExcludedExtensionMsg", ext=new_exclusion), parent=self)
    def remove_exclusion(self):
        _ = self._; selected_indices = self.exclusion_listbox.curselection()
        if not selected_indices: messagebox.showwarning(_("NoSelectionWarningTitle"), _("NoExclusionSelectedMsg"), parent=self); return
        selected_exclusion = self.exclusion_listbox.get(selected_indices[0])
        if messagebox.askyesno(_("ConfirmRemoveTitle"), _("ConfirmRemoveExclusionMsg", ext=selected_exclusion), parent=self):
            if selected_exclusion in self.edited_excluded_extensions: self.edited_excluded_extensions.remove(selected_exclusion); self.populate_exclusion_list()
    def save_changes(self):
        _ = self._; config_data_to_save = {"Kategorien": self.edited_categories, "StandardKategorie": self.original_default_category, "AusgeschlosseneEndungen": sorted(list(self.edited_excluded_extensions)), "AusgeschlosseneOrdner": sorted(list(self.edited_excluded_folders))}
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f: json.dump(config_data_to_save, f, indent=4, ensure_ascii=False)
            self.destroy()
        except OSError as e: messagebox.showerror(_("SaveErrorTitle"), _("SaveErrorMsg", error=e), parent=self)
        except Exception as e: messagebox.showerror(_("ErrorTitle"), _("UnexpectedSaveErrorMsg", error=e), parent=self)
    def cancel_changes(self): self.destroy()

# -----------------------------------------------------------------------------
# Klasse InfoWindow (mit Logo und Übersetzung)
# -----------------------------------------------------------------------------
class InfoWindow(tk.Toplevel):
    def __init__(self, parent, current_year, app_version, translator_func):
        super().__init__(parent); self.transient(parent); self.parent = parent; self._ = translator_func
        self.title(self._("InfoWindowTitle", default="Info")); self.resizable(False, False); self.protocol("WM_DELETE_WINDOW", self.destroy)
        info_frame = ttk.Frame(self, padding="15"); info_frame.pack(expand=True, fill=tk.BOTH)
        try: script_dir = os.path.dirname(os.path.abspath(__file__))
        except NameError: script_dir = os.getcwd()
        logo_path = os.path.join(script_dir, 'img', 'logo.jpg')
        self.logo_image = None
        try:
            if not PIL_AVAILABLE: raise ImportError(self._("PillowMissingError", default="Pillow (PIL) fehlt"))
            img = Image.open(logo_path); max_size = (200, 200); img.thumbnail(max_size, Image.Resampling.LANCZOS)
            self.logo_image = ImageTk.PhotoImage(img); logo_label = ttk.Label(info_frame, image=self.logo_image); logo_label.pack(pady=(0, 15))
        except FileNotFoundError: ttk.Label(info_frame, text=self._("LogoNotFoundError", default="Logo nicht gefunden:\n{path}", path=logo_path)).pack(pady=10)
        except ImportError as e: ttk.Label(info_frame, text=f"{e}\n(pip install Pillow)").pack(pady=10)
        except Exception as e: ttk.Label(info_frame, text=self._("LogoLoadError", default="Fehler Laden Logo:\n{error}", error=e), justify=tk.LEFT).pack(pady=10)
        copyright_text = self._("AppInfoText", default="Dateiexperte\nVersion {version}\n\nCopyright {year} @ {author}", app_name=self._("AppTitle"), version=app_version, year=current_year, author="Knut Wehr")
        text_label = ttk.Label(info_frame, text=copyright_text, justify=tk.CENTER); text_label.pack(pady=(0, 15))
        ok_button = ttk.Button(info_frame, text=self._("OkButton", default="OK"), command=self.destroy, style="Accent.TButton"); ok_button.pack(pady=(5, 0))
        ok_button.focus_set(); self.bind("<Return>", lambda event: self.destroy())
        self.update_idletasks(); parent_x = parent.winfo_rootx(); parent_y = parent.winfo_rooty(); parent_width = parent.winfo_width(); parent_height = parent.winfo_height(); dialog_width = self.winfo_reqwidth(); dialog_height = self.winfo_reqheight(); x = max(0, parent_x + (parent_width // 2) - (dialog_width // 2)); y = max(0, parent_y + (parent_height // 2) - (dialog_height // 2)); self.geometry(f'+{x}+{y}')
        self.grab_set(); self.wait_window()

# -----------------------------------------------------------------------------
# Klasse FileInfoDialog (mit Übersetzung)
# -----------------------------------------------------------------------------
class FileInfoDialog(tk.Toplevel):
    def __init__(self, parent, info_dict, translator_func):
        super().__init__(parent); self.transient(parent); self.parent = parent; self._ = translator_func
        file_title = info_dict.get(self._("FileInfoLabelFilename", default="Dateiname"), self._("DefaultFileTitle", default="Datei"))
        self.title(self._("FileInfoDialogTitle", default="Infos für: {filename}", filename=file_title))
        self.resizable(False, False); self.protocol("WM_DELETE_WINDOW", self.destroy); self.value_vars = []
        main_frame = ttk.Frame(self, padding="15"); main_frame.pack(expand=True, fill=tk.BOTH)
        info_frame = ttk.Frame(main_frame); info_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10)); info_frame.columnconfigure(1, weight=1)
        row_index = 0
        for key, value in info_dict.items():
            lbl_key = ttk.Label(info_frame, text=f"{key}:"); lbl_key.grid(row=row_index, column=0, sticky="nw", padx=(0, 10), pady=2)
            val_var = tk.StringVar(value=value); self.value_vars.append(val_var)
            entry_val = ttk.Entry(info_frame, textvariable=val_var, state="readonly", width=70); entry_val.grid(row=row_index, column=1, sticky="ew", pady=2)
            row_index += 1
        ok_button_frame = ttk.Frame(main_frame); ok_button_frame.pack(fill=tk.X, pady=(10, 0))
        ok_button = ttk.Button(ok_button_frame, text=self._("OkButton", default="OK"), command=self.destroy, style="Accent.TButton"); ok_button.pack()
        ok_button.focus_set(); self.bind("<Return>", lambda event: self.destroy())
        self.update_idletasks(); parent_x = parent.winfo_rootx(); parent_y = parent.winfo_rooty(); parent_width = parent.winfo_width(); parent_height = parent.winfo_height(); dialog_width = self.winfo_reqwidth(); dialog_height = self.winfo_reqheight(); x = max(0, parent_x + (parent_width // 2) - (dialog_width // 2)); y = max(0, parent_y + (parent_height // 2) - (dialog_height // 2)); self.geometry(f'+{x}+{y}')
        self.grab_set(); self.wait_window()

# -----------------------------------------------------------------------------
# Hauptausführung: Startet die Anwendung
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    try: locale.setlocale(locale.LC_ALL, '')
    except locale.Error as e: print(f"Warnung: Locale konnte nicht gesetzt werden ({e}). Verwende System-Standard.")
    root = tk.Tk()
    app = FileSorterApp(root)
    root.mainloop()