# -*- coding: utf-8 -*-
"""
Dateiexperte v2.0.0 - Refactored Version
File sorting application with improved architecture and reduced complexity.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import os
import threading
import datetime
import locale

# Import new components
from config_models import ConfigManager, SorterConfig
from file_sorter import FileSorter, SortResult
from ui_components import (
    StatusLogger, MenuBuilder, ProgressTracker,
    DialogPositioner, safe_gui_operation
)

# Pillow import
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Translator import
try:
    from translator import Translator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    print("FEHLER: translator.py nicht gefunden.")
    TRANSLATOR_AVAILABLE = False

def dummy_get_string(key, default=None, **kwargs):
    """Fallback translation function."""
    text = default if default is not None else key
    if kwargs:
        try:
            return text.format(**kwargs)
        except KeyError:
            return text + " " + str(kwargs)
    return text


class FileSorterApp:
    """Main application class - refactored version."""
    
    CONFIG_FILENAME = "sorter_config.json"
    APP_VERSION = "2.0.0"
    
    def __init__(self, master):
        self.master = master
        self.current_year = datetime.date.today().year
        
        # Initialize core components
        self._initialize_translator()
        self._setup_window()
        self._initialize_config()
        self._initialize_ui_components()
        self._create_gui()
        self._setup_menu()
        self._log_startup_info()
    
    def _initialize_translator(self):
        """Initialize the translation system."""
        self._ = dummy_get_string
        self.translator = None
        
        if TRANSLATOR_AVAILABLE:
            try:
                sys_lang = locale.getlocale()[0].split('_')[0].lower()
            except:
                sys_lang = 'en'
            
            supported_langs = ['en', 'de', 'fr', 'es', 'pl']
            initial_lang = sys_lang if sys_lang in supported_langs else 'en'
            
            try:
                self.translator = Translator(
                    language_code=initial_lang,
                    default_lang='en'
                )
                self._ = self.translator.get_string
                print(f"Translator initialisiert mit Sprache: {self.translator.language}")
            except Exception as e:
                print(f"FEHLER bei Translator-Initialisierung: {e}")
                messagebox.showerror(
                    "Übersetzungsfehler",
                    f"Übersetzungsmodul nicht initialisiert:\n{e}"
                )
    
    def _setup_window(self):
        """Configure the main window."""
        self.master.title(self._("AppTitle", default="Dateiexperte"))
        self.master.geometry("650x500")
        self.master.minsize(600, 450)
    
    def _initialize_config(self):
        """Initialize configuration management."""
        self.config_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            self.CONFIG_FILENAME
        )
        self.config_manager = ConfigManager(self.config_file, self.log)
        self.config = self.config_manager.load_config()
        self.file_sorter = FileSorter(self.config, self.log)
    
    def _initialize_ui_components(self):
        """Initialize UI component helpers."""
        # Variables
        self.source_dir = tk.StringVar()
        self.target_dir = tk.StringVar()
        self.operation_type = tk.StringVar(value="copy")
        
        # Will be initialized after GUI creation
        self.status_logger = None
        self.progress_tracker = None
    
    def _create_gui(self):
        """Create the main GUI layout."""
        # Main frame
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1)
        
        # Create GUI sections
        self._create_folder_selection(main_frame)
        self._create_operation_selection(main_frame)
        self._create_action_buttons(main_frame)
        self._create_progress_section(main_frame)
        self._create_status_section(main_frame)
        
        # Initialize helpers after GUI creation
        self.status_logger = StatusLogger(self.status_text)
        self.progress_tracker = ProgressTracker(self.progress_bar, self.master)
    
    def _create_folder_selection(self, parent):
        """Create folder selection widgets."""
        # Source folder
        row = 0
        ttk.Label(parent, text=self._("SourceFolderLabel", default="Quellordner:")
        ).grid(row=row, column=0, padx=5, pady=5, sticky="w")
        
        self.source_entry = ttk.Entry(parent, textvariable=self.source_dir, width=60)
        self.source_entry.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Button(
            parent,
            text=self._("BrowseButton", default="Durchsuchen..."),
            command=self.browse_source
        ).grid(row=row, column=2, padx=5, pady=5)
        
        # Target folder
        row = 1
        ttk.Label(parent, text=self._("TargetFolderLabel", default="Zielordner:")
        ).grid(row=row, column=0, padx=5, pady=5, sticky="w")
        
        self.target_entry = ttk.Entry(parent, textvariable=self.target_dir, width=60)
        self.target_entry.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
        
        ttk.Button(
            parent,
            text=self._("BrowseButton", default="Durchsuchen..."),
            command=self.browse_target
        ).grid(row=row, column=2, padx=5, pady=5)
    
    def _create_operation_selection(self, parent):
        """Create operation type selection."""
        option_frame = ttk.Frame(parent)
        option_frame.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="w")
        
        ttk.Label(option_frame, text=self._("ActionButton", default="Aktion:")
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Radiobutton(
            option_frame,
            text=self._("CopyRadioButton", default="Kopieren"),
            variable=self.operation_type,
            value="copy"
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Radiobutton(
            option_frame,
            text=self._("MoveRadioButton", default="Verschieben"),
            variable=self.operation_type,
            value="move"
        ).pack(side=tk.LEFT, padx=5)
    
    def _create_action_buttons(self, parent):
        """Create action buttons."""
        self.start_button = ttk.Button(
            parent,
            text=self._("StartButton", default="Sortieren starten"),
            command=self.start_sorting_thread,
            style="Accent.TButton"
        )
        
        style = ttk.Style()
        style.configure("Accent.TButton", foreground="white", background="#0078D7")
        
        self.start_button.grid(row=3, column=0, columnspan=3, pady=15)
    
    def _create_progress_section(self, parent):
        """Create progress bar."""
        self.progress_bar = ttk.Progressbar(
            parent,
            orient="horizontal",
            length=400,
            mode="determinate"
        )
        self.progress_bar.grid(row=4, column=0, columnspan=3, pady=5, padx=5, sticky="ew")
    
    def _create_status_section(self, parent):
        """Create status/log section."""
        ttk.Label(
            parent,
            text=self._("StatusLabel", default="Status / Log:")
        ).grid(row=5, column=0, columnspan=3, padx=5, pady=(10,0), sticky="w")
        
        self.status_text = scrolledtext.ScrolledText(
            parent,
            height=12,
            width=80,
            state='disabled',
            wrap=tk.WORD
        )
        self.status_text.grid(row=6, column=0, columnspan=3, padx=5, pady=(0,10), sticky="nsew")
    
    def _setup_menu(self):
        """Setup application menu."""
        menu_builder = MenuBuilder(self.master, self._)
        menu_builder.build_menu({
            'file_info': self.show_file_info,
            'category_editor': self.open_category_editor,
            'info_window': self.show_info_window
        })
    
    def _log_startup_info(self):
        """Log initial startup information."""
        self.log(self._(
            "AppStartLog",
            default="App gestartet (v{version}). Konfig: {config}",
            version=self.APP_VERSION,
            config=self.config_file
        ))
        
        if not PIL_AVAILABLE:
            self.log(self._("PillowWarningLog", default="WARNUNG: Pillow nicht gefunden."))
        
        self.log(self._(
            "DefaultTargetLog",
            default="Standard-Ziel: '{target}'",
            target=self.config.default_category
        ))
        
        extension_count = len(self.config.build_extension_map())
        self.log(self._(
            "MappingInfoLog",
            default="{ext_count} Endungen gemappt.",
            ext_count=extension_count
        ))
        
        if self.config.excluded_extensions:
            self.log(self._(
                "ExclusionInfoExtLog",
                default="{count} Endungen ausgeschlossen.",
                count=len(self.config.excluded_extensions)
            ))
        
        if self.config.excluded_folders:
            self.log(self._(
                "ExclusionInfoFolderLog",
                default="{count} Ordner ausgeschlossen.",
                count=len(self.config.excluded_folders)
            ))
    
    def log(self, message):
        """Log a message (compatibility wrapper)."""
        if self.status_logger:
            self.status_logger.log(message)
        else:
            # During initialization
            print(f"[INIT] {message}")
    
    def browse_source(self):
        """Browse for source directory."""
        directory = filedialog.askdirectory(
            title=self._("BrowseSourceTitle", default="Quellordner auswählen"),
            mustexist=True,
            parent=self.master
        )
        if directory:
            self.source_dir.set(directory)
            self.log(self._("SourceSelectedLog", default="Quellordner: {folder}", folder=directory))
    
    def browse_target(self):
        """Browse for target directory."""
        directory = filedialog.askdirectory(
            title=self._("BrowseTargetTitle", default="Zielordner auswählen"),
            parent=self.master
        )
        if directory:
            self.target_dir.set(directory)
            self.log(self._("TargetSelectedLog", default="Zielordner: {folder}", folder=directory))
    
    def show_file_info(self):
        """Show file information dialog."""
        from file_info_dialog import show_file_info_dialog
        show_file_info_dialog(self.master, self._)
    
    def show_info_window(self):
        """Show application info window."""
        if not PIL_AVAILABLE:
            messagebox.showwarning(
                self._("PillowMissingWarningTitle", default="Pillow fehlt"),
                self._("PillowMissingWarningMsg", default="Pillow fehlt..."),
                parent=self.master
            )
            messagebox.showinfo(
                self._("InfoWindowTitle", default="Info"),
                self._("AppInfoFallbackText", default="App Info...",
                      version=self.APP_VERSION, year=self.current_year),
                parent=self.master
            )
            return
        
        from info_window import InfoWindow
        InfoWindow(self.master, self.current_year, self.APP_VERSION, self._)
    
    def open_category_editor(self):
        """Open category editor dialog."""
        from category_editor import CategoryEditor
        editor = CategoryEditor(
            self.master,
            self.config_manager,
            self.config,
            self._
        )
        
        # Reload configuration after editing
        self.log(self._("ConfigReloadLog", default="Lade Konfig nach Bearbeitung neu..."))
        self.config = self.config_manager.load_config()
        self.file_sorter = FileSorter(self.config, self.log)
        
        extension_count = len(self.config.build_extension_map())
        self.log(self._(
            "ConfigReloadedLog",
            default="Konfig neu geladen.",
            ext_count=extension_count,
            excl_ext_count=len(self.config.excluded_extensions),
            excl_fld_count=len(self.config.excluded_folders)
        ))
    
    def start_sorting_thread(self):
        """Start file sorting in a separate thread."""
        source = self.source_dir.get()
        target = self.target_dir.get()
        operation = self.operation_type.get()
        
        # Validate directories
        error = self.file_sorter.validate_directories(source, target)
        if error:
            messagebox.showerror(self._("ErrorTitle"), self._(error), parent=self.master)
            return
        
        # Handle missing target directory
        if not os.path.exists(target):
            if self._should_create_target(target):
                try:
                    os.makedirs(target, exist_ok=True)
                    self.log(self._("TargetCreatedLog", folder=target))
                except OSError as e:
                    messagebox.showerror(
                        self._("ErrorTitle"),
                        self._("TargetCreateErrorMsg", error=e),
                        parent=self.master
                    )
                    return
            else:
                return
        
        # Start sorting
        self.start_button.config(state="disabled")
        self.progress_tracker.reset()
        
        self.log(self._(
            "StartLog",
            action=operation.upper(),
            source=source,
            target=target
        ))
        
        thread = threading.Thread(
            target=self._sort_files_thread,
            args=(source, target, operation),
            daemon=True
        )
        thread.start()
    
    def _should_create_target(self, target):
        """Ask user if target directory should be created."""
        return messagebox.askyesno(
            self._("TargetCreateTitle"),
            self._("TargetCreateMsg", path=target),
            icon='question',
            parent=self.master
        )
    
    def _sort_files_thread(self, source, target, operation):
        """Thread function for file sorting."""
        try:
            # Set up progress callback
            def progress_callback(current):
                self.progress_tracker.update(current)
            
            # Perform sorting
            result = self.file_sorter.sort_files(
                source, target, operation,
                progress_callback=progress_callback
            )
            
            # Update progress tracker maximum
            if result.total > 0:
                self.master.after(0, self.progress_tracker.set_maximum, result.total)
            
            # Show completion
            self.master.after(0, self._show_completion_message, result)
            
        except Exception as e:
            self.master.after(0, self.log, self._("FatalThreadErrorLog", error=e))
            self.master.after(0, messagebox.showerror,
                            self._("FatalErrorTitle"),
                            self._("FatalThreadErrorMsg", error=e))
        finally:
            self.master.after(0, self._enable_start_button)
    
    def _show_completion_message(self, result: SortResult):
        """Show completion message based on sorting results."""
        _ = self._
        
        # Build log message
        if result.total == 0:
            log_msg = _("LogCompletionNoFiles", default="Vorgang beendet. Keine Dateien zum Verarbeiten gefunden.")
            info_msg = _("MsgCompletionNoFiles", default="Keine Dateien im Quellordner gefunden.")
            title = _("CompletionTitleSuccess", default="Fertig")
            msg_type = "info"
        else:
            log_msg = _(
                "LogCompletion",
                default="Vorgang abgeschlossen. {success} Dateien erfolgreich verarbeitet.",
                success=result.processed
            )
            info_msg = _(
                "CompletionMsgSuccess",
                default="Sortierung abgeschlossen!\n\nErfolgreich: {success}",
                success=result.processed
            )
            
            if result.skipped > 0:
                log_msg += _(
                    "LogCompletionSkipped",
                    default=" {skipped} übersprungen.",
                    skipped=result.skipped
                )
                info_msg += _(
                    "CompletionMsgSkipped",
                    default="\nÜbersprungen: {skipped}",
                    skipped=result.skipped
                )
            
            if result.errors > 0:
                log_msg += _(
                    "LogCompletionError",
                    default=" {errors} FEHLER.",
                    errors=result.errors
                )
                info_msg += _(
                    "CompletionMsgError",
                    default="\nFehler: {errors}",
                    errors=result.errors
                )
                title = _("CompletionTitleWarning", default="Fertig mit Fehlern/Warnungen")
                msg_type = "warning"
            else:
                title = _("CompletionTitleSuccess", default="Fertig")
                msg_type = "info"
        
        # Log and show message
        self.log(_("LogSeparator", default="--------------------"))
        self.log(log_msg)
        
        if msg_type == "info":
            messagebox.showinfo(title, info_msg, parent=self.master)
        else:
            messagebox.showwarning(title, info_msg, parent=self.master)
        
        self.progress_tracker.reset()
    
    def _enable_start_button(self):
        """Re-enable the start button."""
        try:
            if self.master.winfo_exists():
                self.start_button.config(state="normal")
        except tk.TclError:
            pass


def main():
    """Main entry point."""
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error as e:
        print(f"Warnung: Locale konnte nicht gesetzt werden ({e}). Verwende System-Standard.")
    
    root = tk.Tk()
    app = FileSorterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()