# -*- coding: utf-8 -*-
"""
Reusable UI components for Dateiexperte.
Eliminates duplication and provides consistent UI behavior.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional, Callable, Tuple
import datetime
from contextlib import contextmanager


class ListboxManager:
    """Generic manager for listbox operations to eliminate duplication."""
    
    def __init__(self, listbox: tk.Listbox):
        self.listbox = listbox
    
    def populate(self, items: List[str], selected_value: Optional[str] = None) -> None:
        """Populate listbox with items, optionally selecting one."""
        # Save current selection if no specific value requested
        if selected_value is None:
            selection = self.listbox.curselection()
            if selection:
                selected_value = self.listbox.get(selection[0])
        
        # Clear and repopulate
        self.listbox.delete(0, tk.END)
        
        # Add sorted items
        sorted_items = sorted(items)
        new_selection_index = -1
        
        for i, item in enumerate(sorted_items):
            self.listbox.insert(tk.END, item)
            if item == selected_value:
                new_selection_index = i
        
        # Restore selection
        if new_selection_index != -1:
            self._select_item(new_selection_index)
    
    def get_selected(self) -> Optional[str]:
        """Get currently selected item."""
        selection = self.listbox.curselection()
        if selection:
            return self.listbox.get(selection[0])
        return None
    
    def add_item(self, item: str, select: bool = True) -> bool:
        """Add item to listbox if not already present."""
        items = list(self.listbox.get(0, tk.END))
        if item in items:
            return False
        
        # Add and repopulate to maintain sort
        items.append(item)
        self.populate(items, item if select else None)
        return True
    
    def remove_selected(self) -> Optional[str]:
        """Remove currently selected item."""
        selected = self.get_selected()
        if selected:
            items = list(self.listbox.get(0, tk.END))
            items.remove(selected)
            self.populate(items)
        return selected
    
    def _select_item(self, index: int) -> None:
        """Select item at given index."""
        try:
            self.listbox.select_clear(0, tk.END)
            self.listbox.select_set(index)
            self.listbox.activate(index)
            self.listbox.see(index)
        except tk.TclError:
            pass


class StatusLogger:
    """Handles status text logging with timestamps."""
    
    def __init__(self, text_widget: tk.Text):
        self.text_widget = text_widget
    
    def log(self, message: str) -> None:
        """Log a message with timestamp."""
        try:
            self.text_widget.config(state='normal')
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            self.text_widget.insert(tk.END, f"[{timestamp}] {message}\n")
            self.text_widget.see(tk.END)
            self.text_widget.config(state='disabled')
        except tk.TclError:
            pass
        except Exception as e:
            print(f"Log-Fehler: {e}")


class MenuBuilder:
    """Builds application menus."""
    
    def __init__(self, master: tk.Tk, translator: Callable):
        self.master = master
        self._ = translator
    
    def build_menu(self, callbacks: dict) -> tk.Menu:
        """Build the application menu bar."""
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(
            label=self._("EditMenu", default="Bearbeiten"), 
            menu=edit_menu
        )
        edit_menu.add_command(
            label=self._("FileInfoMenuItem", default="Datei-Info..."),
            command=callbacks.get('file_info')
        )
        
        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(
            label=self._("SettingsMenu", default="Einstellungen"),
            menu=settings_menu
        )
        settings_menu.add_command(
            label=self._("CategoriesMenuItem", default="Kategorien & Ausschlüsse..."),
            command=callbacks.get('category_editor')
        )
        
        # Info menu
        info_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(
            label=self._("InfoMenu", default="Info"),
            menu=info_menu
        )
        info_menu.add_command(
            label=self._("CopyrightMenuItem", default="Info / Copyright"),
            command=callbacks.get('info_window')
        )
        
        return menubar


class DialogPositioner:
    """Centers dialogs over their parent windows."""
    
    @staticmethod
    def center_on_parent(dialog: tk.Toplevel, parent: tk.Widget) -> None:
        """Center a dialog on its parent window."""
        dialog.update_idletasks()
        
        # Get parent position and size
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        # Get dialog size
        dialog_width = dialog.winfo_reqwidth()
        dialog_height = dialog.winfo_reqheight()
        
        # Calculate position
        x = max(0, parent_x + (parent_width // 2) - (dialog_width // 2))
        y = max(0, parent_y + (parent_height // 2) - (dialog_height // 2))
        
        dialog.geometry(f'+{x}+{y}')


class ValidationHelper:
    """Common validation methods for user input."""
    
    @staticmethod
    def validate_extension(ext: str, translator: Callable) -> Tuple[bool, str, str]:
        """
        Validate a file extension.
        Returns: (is_valid, cleaned_extension, error_message)
        """
        _ = translator
        ext = ext.strip().lower()
        
        if not ext:
            return False, "", _("EmptyInputExtensionMsg", default="Keine Endung eingegeben.")
        
        # Ensure it starts with a dot
        if not ext.startswith('.'):
            ext = '.' + ext
        
        # Check minimum length
        if len(ext) < 2:
            return False, ext, _("InvalidExtensionWarningMsg", default=f"Ungültige Endung: {ext}")
        
        return True, ext, ""
    
    @staticmethod
    def validate_folder_name(folder: str, translator: Callable) -> Tuple[bool, str, str]:
        """
        Validate a folder name.
        Returns: (is_valid, cleaned_name, error_message)
        """
        _ = translator
        folder = folder.strip()
        
        if not folder:
            return False, "", _("EmptyInputFolderMsg", default="Kein Ordnername eingegeben.")
        
        # Check for path separators
        import os
        if os.sep in folder or (os.altsep and os.altsep in folder):
            return False, folder, _("InvalidFolderNameWarningMsg", default="Ordnername darf keine Pfadtrenner enthalten.")
        
        return True, folder.lower(), ""


@contextmanager
def safe_gui_operation(parent: tk.Widget, operation_name: str, translator: Callable):
    """
    Context manager for safe GUI operations with error handling.
    """
    _ = translator
    try:
        yield
    except tk.TclError as e:
        # GUI-specific errors
        messagebox.showerror(
            _("ErrorTitle", default="Fehler"),
            _(f"{operation_name}TclError", default=f"{operation_name} GUI-Fehler: {e}"),
            parent=parent
        )
    except Exception as e:
        # General errors
        messagebox.showerror(
            _("ErrorTitle", default="Fehler"),
            _(f"{operation_name}Error", default=f"{operation_name} Fehler: {e}"),
            parent=parent
        )


class InputDialog:
    """Reusable input dialog with validation."""
    
    def __init__(self, parent: tk.Widget, title: str, prompt: str, 
                 validator: Optional[Callable] = None):
        self.parent = parent
        self.title = title
        self.prompt = prompt
        self.validator = validator
        self.result = None
    
    def show(self) -> Optional[str]:
        """Show dialog and return validated input."""
        from tkinter import simpledialog
        
        while True:
            value = simpledialog.askstring(self.title, self.prompt, parent=self.parent)
            
            if value is None:  # User cancelled
                return None
            
            if self.validator:
                is_valid, cleaned_value, error_msg = self.validator(value)
                if is_valid:
                    return cleaned_value
                else:
                    messagebox.showwarning(
                        self.title,
                        error_msg,
                        parent=self.parent
                    )
            else:
                return value.strip()


class ProgressTracker:
    """Manages progress bar updates."""
    
    def __init__(self, progress_bar: ttk.Progressbar, master: tk.Widget):
        self.progress_bar = progress_bar
        self.master = master
    
    def set_maximum(self, maximum: int) -> None:
        """Set the maximum value for the progress bar."""
        self.progress_bar['maximum'] = maximum
    
    def update(self, value: int) -> None:
        """Update progress bar value safely."""
        def _update():
            try:
                if self.master.winfo_exists():
                    self.progress_bar['value'] = value
            except tk.TclError:
                pass
        
        self.master.after(0, _update)
    
    def reset(self) -> None:
        """Reset progress bar to zero."""
        self.update(0)