# -*- coding: utf-8 -*-
"""
Application info window component.
"""

import os
import tkinter as tk
from tkinter import ttk
from typing import Callable
from ui_components import DialogPositioner

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class InfoWindow(tk.Toplevel):
    """Application information window with logo."""
    
    def __init__(self, parent: tk.Widget, current_year: int, app_version: str, translator_func: Callable):
        super().__init__(parent)
        self.transient(parent)
        self.parent = parent
        self._ = translator_func
        
        # Window setup
        self.title(self._("InfoWindowTitle", default="Info"))
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        
        # Create UI
        self._create_ui(current_year, app_version)
        
        # Center on parent
        DialogPositioner.center_on_parent(self, parent)
        
        # Modal behavior
        self.grab_set()
        self.wait_window()
    
    def _create_ui(self, current_year: int, app_version: str) -> None:
        """Create the info window UI."""
        info_frame = ttk.Frame(self, padding="15")
        info_frame.pack(expand=True, fill=tk.BOTH)
        
        # Logo
        self._add_logo(info_frame)
        
        # Info text
        copyright_text = self._(
            "AppInfoText",
            default="Dateiexperte\nVersion {version}\n\nCopyright {year} @ {author}",
            app_name=self._("AppTitle"),
            version=app_version,
            year=current_year,
            author="Knut Wehr"
        )
        
        text_label = ttk.Label(info_frame, text=copyright_text, justify=tk.CENTER)
        text_label.pack(pady=(0, 15))
        
        # OK button
        ok_button = ttk.Button(
            info_frame,
            text=self._("OkButton", default="OK"),
            command=self.destroy,
            style="Accent.TButton"
        )
        ok_button.pack(pady=(5, 0))
        ok_button.focus_set()
        
        # Bind Enter key
        self.bind("<Return>", lambda e: self.destroy())
    
    def _add_logo(self, parent: ttk.Frame) -> None:
        """Add logo to the info window."""
        if not PIL_AVAILABLE:
            error_label = ttk.Label(
                parent,
                text=self._("PillowMissingError", default="Pillow (PIL) fehlt\n(pip install Pillow)")
            )
            error_label.pack(pady=10)
            return
        
        # Find logo path
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            script_dir = os.getcwd()
        
        logo_path = os.path.join(script_dir, 'img', 'logo.jpg')
        
        try:
            # Load and resize logo
            img = Image.open(logo_path)
            max_size = (200, 200)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Convert to PhotoImage
            self.logo_image = ImageTk.PhotoImage(img)
            
            # Display
            logo_label = ttk.Label(parent, image=self.logo_image)
            logo_label.pack(pady=(0, 15))
            
        except FileNotFoundError:
            error_label = ttk.Label(
                parent,
                text=self._("LogoNotFoundError", default="Logo nicht gefunden:\n{path}", path=logo_path)
            )
            error_label.pack(pady=10)
        except Exception as e:
            error_label = ttk.Label(
                parent,
                text=self._("LogoLoadError", default="Fehler Laden Logo:\n{error}", error=e),
                justify=tk.LEFT
            )
            error_label.pack(pady=10)