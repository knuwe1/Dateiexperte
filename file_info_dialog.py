# -*- coding: utf-8 -*-
"""
File information dialog component.
"""

import os
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Dict
from ui_components import DialogPositioner


def format_size(size_bytes: int, translator: Callable) -> str:
    """Format file size in human-readable format."""
    _ = translator
    
    if size_bytes < 0:
        return "N/A"
    
    if size_bytes < 1024:
        return f"{size_bytes} {_('BytesSuffix', default='Bytes')}"
    elif size_bytes < 1024**2:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes / (1024**2):.2f} MB"
    else:
        return f"{size_bytes / (1024**3):.2f} GB"


def gather_file_info(file_path: str, translator: Callable) -> Dict[str, str]:
    """Gather information about a file."""
    _ = translator
    stats = os.stat(file_path)
    info = {}
    
    # Basic info
    info[_("FileInfoLabelFilename", default="Dateiname")] = os.path.basename(file_path)
    info[_("FileInfoLabelFullPath", default="Voller Pfad")] = os.path.abspath(file_path)
    info[_("FileInfoLabelDirectory", default="Verzeichnis")] = os.path.dirname(os.path.abspath(file_path))
    
    # Size
    size_str = f"{format_size(stats.st_size, _)} ({stats.st_size:,} {_('BytesSuffix', default='Bytes')})"
    info[_("FileInfoLabelSize", default="Größe")] = size_str.replace(",", ".")
    
    # Timestamps
    dt_format = _("DateTimeFormat", default="%d.%m.%Y %H:%M:%S")
    created_suffix = _("FileInfoCreatedSuffix", default=" (Metadaten)")
    
    try:
        info[_("FileInfoLabelCreated", default="Erstellt")] = (
            datetime.datetime.fromtimestamp(stats.st_ctime).strftime(dt_format) + 
            created_suffix
        )
    except OSError:
        info[_("FileInfoLabelCreated", default="Erstellt")] = "N/A"
    
    try:
        info[_("FileInfoLabelModified", default="Geändert")] = (
            datetime.datetime.fromtimestamp(stats.st_mtime).strftime(dt_format)
        )
    except OSError:
        info[_("FileInfoLabelModified", default="Geändert")] = "N/A"
    
    try:
        info[_("FileInfoLabelAccessed", default="Zugriff")] = (
            datetime.datetime.fromtimestamp(stats.st_atime).strftime(dt_format)
        )
    except OSError:
        info[_("FileInfoLabelAccessed", default="Zugriff")] = "N/A"
    
    # Extension
    basename_part, extension = os.path.splitext(os.path.basename(file_path))
    no_ext_str = _("FileInfoNoExtension", default="(Keine)")
    info[_("FileInfoLabelExtension", default="Dateiendung")] = extension if extension else no_ext_str
    
    return info


def show_file_info_dialog(parent: tk.Widget, translator: Callable) -> None:
    """Show file information dialog."""
    _ = translator
    
    # Get file path
    file_path = filedialog.askopenfilename(
        title=_("SelectFileInfoTitle", default="Datei für Info wählen"),
        parent=parent
    )
    
    if not file_path:
        return
    
    try:
        # Gather file information
        info_dict = gather_file_info(file_path, _)
        
        # Show dialog
        FileInfoDialog(parent, info_dict, _)
        
    except FileNotFoundError:
        messagebox.showerror(
            _("FileInfoErrorTitle", default="Fehler"),
            _("FileInfoNotFoundErrorMsg", default="Datei nicht gefunden:\n{path}", path=file_path),
            parent=parent
        )
    except PermissionError:
        messagebox.showerror(
            _("FileInfoErrorTitle", default="Fehler"),
            _("FileInfoPermissionErrorMsg", default="Keine Rechte für:\n{path}", path=file_path),
            parent=parent
        )
    except Exception as e:
        messagebox.showerror(
            _("FileInfoErrorTitle", default="Fehler"),
            _("FileInfoGenericErrorMsg", default="Fehler beim Abrufen:\n{error}", error=str(e)),
            parent=parent
        )


class FileInfoDialog(tk.Toplevel):
    """Dialog showing file information."""
    
    def __init__(self, parent: tk.Widget, info_dict: Dict[str, str], translator_func: Callable):
        super().__init__(parent)
        self.transient(parent)
        self.parent = parent
        self._ = translator_func
        
        # Get filename for title
        filename_key = translator_func("FileInfoLabelFilename", default="Dateiname")
        file_title = info_dict.get(filename_key, translator_func("DefaultFileTitle", default="Datei"))
        
        self.title(self._("FileInfoDialogTitle", default="Infos für: {filename}", filename=file_title))
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        
        # Create UI
        self._create_ui(info_dict)
        
        # Center on parent
        DialogPositioner.center_on_parent(self, parent)
        
        # Modal behavior
        self.grab_set()
        self.wait_window()
    
    def _create_ui(self, info_dict: Dict[str, str]) -> None:
        """Create the dialog UI."""
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(expand=True, fill=tk.BOTH)
        
        # Info frame
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        info_frame.columnconfigure(1, weight=1)
        
        # Display each piece of information
        for row, (key, value) in enumerate(info_dict.items()):
            # Label
            lbl = ttk.Label(info_frame, text=f"{key}:")
            lbl.grid(row=row, column=0, sticky="nw", padx=(0, 10), pady=2)
            
            # Value (in read-only entry for easy copying)
            entry = ttk.Entry(info_frame, width=70)
            entry.insert(0, value)
            entry.config(state="readonly")
            entry.grid(row=row, column=1, sticky="ew", pady=2)
        
        # OK button
        ok_frame = ttk.Frame(main_frame)
        ok_frame.pack(fill=tk.X, pady=(10, 0))
        
        ok_button = ttk.Button(
            ok_frame,
            text=self._("OkButton", default="OK"),
            command=self.destroy
        )
        ok_button.pack()
        ok_button.focus_set()
        
        # Bind Enter key
        self.bind("<Return>", lambda e: self.destroy())