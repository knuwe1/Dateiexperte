# -*- coding: utf-8 -*-
"""
Refactored Category Editor using new UI components.
Manages categories, extensions, and exclusions with reduced duplication.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import copy
from typing import Callable

from config_models import ConfigManager, SorterConfig
from ui_components import (
    ListboxManager, ValidationHelper, InputDialog,
    DialogPositioner, safe_gui_operation
)


class CategoryEditor(tk.Toplevel):
    """Category and exclusion editor dialog - refactored version."""
    
    def __init__(self, parent, config_manager: ConfigManager, 
                 current_config: SorterConfig, translator_func: Callable):
        super().__init__(parent)
        self.transient(parent)
        self.parent = parent
        self._ = translator_func
        
        # Configuration
        self.config_manager = config_manager
        self.original_config = current_config
        self.edited_config = copy.deepcopy(current_config)
        
        # UI managers
        self.category_manager = None
        self.extension_manager = None
        self.exclusion_manager = None
        self.folder_exclusion_manager = None
        
        # Setup
        self._setup_window()
        self._create_ui()
        self._populate_initial_data()
        
        # Modal behavior
        self.protocol("WM_DELETE_WINDOW", self.cancel_changes)
        self.grab_set()
        self.focus_set()
        
        # Center on parent
        DialogPositioner.center_on_parent(self, parent)
        
        self.wait_window()
    
    def _setup_window(self):
        """Configure window properties."""
        self.title(self._("CategoryEditorTitle", default="Kategorien & Ausschlüsse bearbeiten"))
        self.geometry("700x550")
        self.resizable(True, True)
        self.minsize(600, 450)
    
    def _create_ui(self):
        """Create the main UI layout."""
        # Notebook for tabs
        self.notebook = ttk.Notebook(self)
        
        # Create tabs
        self.category_tab = self._create_category_tab()
        self.exclusion_tab = self._create_exclusion_tab()
        self.folder_tab = self._create_folder_exclusion_tab()
        
        # Add tabs to notebook
        self.notebook.add(
            self.category_tab,
            text=self._("CategoriesTab", default="Kategorien")
        )
        self.notebook.add(
            self.exclusion_tab,
            text=self._("ExclusionsTab", default="Ausgeschl. Endungen")
        )
        self.notebook.add(
            self.folder_tab,
            text=self._("FoldersTab", default="Ignorierte Ordner")
        )
        
        self.notebook.pack(expand=True, fill=tk.BOTH, pady=(5, 5), padx=5)
        
        # Button frame
        self._create_button_frame()
    
    def _create_category_tab(self):
        """Create the categories tab."""
        frame = ttk.Frame(self.notebook, padding="10")
        frame.columnconfigure(0, weight=1, minsize=200)
        frame.columnconfigure(1, weight=2)
        frame.rowconfigure(1, weight=1)
        
        # Category list
        ttk.Label(frame, text=self._("CategoryListLabel", default="Kategorien:")
        ).grid(row=0, column=0, sticky="w", pady=(0,2))
        
        cat_list_frame = ttk.Frame(frame)
        cat_list_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        
        cat_scrollbar = ttk.Scrollbar(cat_list_frame, orient=tk.VERTICAL)
        self.category_listbox = tk.Listbox(
            cat_list_frame,
            exportselection=False,
            yscrollcommand=cat_scrollbar.set
        )
        cat_scrollbar.config(command=self.category_listbox.yview)
        cat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.category_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.category_listbox.bind("<<ListboxSelect>>", self._on_category_select)
        
        # Category buttons
        cat_button_frame = ttk.Frame(frame)
        cat_button_frame.grid(row=2, column=0, sticky="ew", pady=(5,0))
        
        ttk.Button(
            cat_button_frame,
            text=self._("AddButton", default="Hinzufügen..."),
            command=self._add_category
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            cat_button_frame,
            text=self._("RemoveButton", default="Entfernen"),
            command=self._remove_category
        ).pack(side=tk.LEFT, padx=2)
        
        # Extension list
        self.extension_label = ttk.Label(
            frame,
            text=self._("ExtensionListLabel", default="Endungen für: {category}", category='-')
        )
        self.extension_label.grid(row=0, column=1, sticky="w", pady=(0,2))
        
        ext_list_frame = ttk.Frame(frame)
        ext_list_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        
        ext_scrollbar = ttk.Scrollbar(ext_list_frame, orient=tk.VERTICAL)
        self.extension_listbox = tk.Listbox(
            ext_list_frame,
            exportselection=False,
            yscrollcommand=ext_scrollbar.set
        )
        ext_scrollbar.config(command=self.extension_listbox.yview)
        ext_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.extension_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Extension input
        ext_input_frame = ttk.Frame(frame)
        ext_input_frame.grid(row=2, column=1, sticky="ew", pady=(5,0))
        
        self.extension_entry = ttk.Entry(ext_input_frame)
        self.extension_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.extension_entry.bind("<Return>", lambda e: self._add_extension())
        
        ttk.Button(
            ext_input_frame,
            text=self._("AddButtonShort", default="Add"),
            command=self._add_extension
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            ext_input_frame,
            text=self._("RemoveButton"),
            command=self._remove_extension
        ).pack(side=tk.LEFT, padx=2)
        
        # Initialize managers
        self.category_manager = ListboxManager(self.category_listbox)
        self.extension_manager = ListboxManager(self.extension_listbox)
        
        return frame
    
    def _create_exclusion_tab(self):
        """Create the extension exclusions tab."""
        frame = ttk.Frame(self.notebook, padding="10")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        
        # List
        ttk.Label(frame, text=self._("ExclusionListLabel", default="Ausgeschl. Endungen:")
        ).grid(row=0, column=0, sticky="w", pady=(0,2))
        
        list_frame = ttk.Frame(frame)
        list_frame.grid(row=1, column=0, sticky="nsew", pady=(0,5))
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.exclusion_listbox = tk.Listbox(
            list_frame,
            exportselection=False,
            yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=self.exclusion_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.exclusion_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Input
        input_frame = ttk.Frame(frame)
        input_frame.grid(row=2, column=0, sticky="ew")
        
        self.exclusion_entry = ttk.Entry(input_frame)
        self.exclusion_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.exclusion_entry.bind("<Return>", lambda e: self._add_exclusion())
        
        ttk.Button(
            input_frame,
            text=self._("AddButtonShort", default="Add"),
            command=self._add_exclusion
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            input_frame,
            text=self._("RemoveButton"),
            command=self._remove_exclusion
        ).pack(side=tk.LEFT, padx=2)
        
        # Initialize manager
        self.exclusion_manager = ListboxManager(self.exclusion_listbox)
        
        return frame
    
    def _create_folder_exclusion_tab(self):
        """Create the folder exclusions tab."""
        frame = ttk.Frame(self.notebook, padding="10")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        
        # List
        ttk.Label(frame, text=self._("FolderExclusionListLabel", default="Ignorierte Ordner:")
        ).grid(row=0, column=0, sticky="w", pady=(0,2))
        
        list_frame = ttk.Frame(frame)
        list_frame.grid(row=1, column=0, sticky="nsew", pady=(0,5))
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.folder_listbox = tk.Listbox(
            list_frame,
            exportselection=False,
            yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=self.folder_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.folder_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Input
        input_frame = ttk.Frame(frame)
        input_frame.grid(row=2, column=0, sticky="ew")
        
        self.folder_entry = ttk.Entry(input_frame)
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.folder_entry.bind("<Return>", lambda e: self._add_folder_exclusion())
        
        ttk.Button(
            input_frame,
            text=self._("AddButtonShort", default="Add"),
            command=self._add_folder_exclusion
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            input_frame,
            text=self._("RemoveButton"),
            command=self._remove_folder_exclusion
        ).pack(side=tk.LEFT, padx=2)
        
        # Initialize manager
        self.folder_exclusion_manager = ListboxManager(self.folder_listbox)
        
        return frame
    
    def _create_button_frame(self):
        """Create the bottom button frame."""
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        # Save button
        save_btn = ttk.Button(
            button_frame,
            text=self._("SaveButton", default="Speichern & Schließen"),
            command=self.save_changes,
            style="Accent.TButton"
        )
        save_btn.pack(side=tk.RIGHT, padx=5)
        
        # Cancel button
        ttk.Button(
            button_frame,
            text=self._("CancelButton", default="Abbrechen"),
            command=self.cancel_changes
        ).pack(side=tk.RIGHT)
        
        # Style
        style = ttk.Style()
        style.configure("Accent.TButton", foreground="white", background="#0078D7")
    
    def _populate_initial_data(self):
        """Populate all lists with initial data."""
        # Categories
        self.category_manager.populate(list(self.edited_config.categories.keys()))
        if self.category_listbox.size() > 0:
            self.category_listbox.select_set(0)
            self._on_category_select(None)
        
        # Exclusions
        self.exclusion_manager.populate(list(self.edited_config.excluded_extensions))
        self.folder_exclusion_manager.populate(list(self.edited_config.excluded_folders))
    
    def _on_category_select(self, event):
        """Handle category selection."""
        selected = self.category_manager.get_selected()
        
        if selected:
            self.extension_label.config(
                text=self._("ExtensionListLabel", default="Endungen für: {category}", 
                          category=selected)
            )
            extensions = self.edited_config.categories.get(selected, [])
            self.extension_manager.populate(extensions)
        else:
            self.extension_label.config(
                text=self._("ExtensionListLabel", default="Endungen für: {category}", 
                          category='-')
            )
            self.extension_manager.populate([])
    
    def _add_category(self):
        """Add a new category."""
        dialog = InputDialog(
            self,
            self._("NewCategoryTitle", default="Neue Kategorie"),
            self._("NewCategoryPrompt", default="Namen eingeben:")
        )
        
        new_category = dialog.show()
        if new_category:
            new_category = new_category.strip()
            
            if not new_category:
                messagebox.showwarning(
                    self._("InvalidNameWarningTitle", default="Ungültiger Name"),
                    self._("InvalidNameWarningMsg", default="Name leer."),
                    parent=self
                )
                return
            
            if new_category in self.edited_config.categories:
                messagebox.showwarning(
                    self._("DuplicateNameWarningTitle", default="Doppelter Name"),
                    self._("DuplicateNameWarningMsg", default="Existiert.", name=new_category),
                    parent=self
                )
            else:
                self.edited_config.categories[new_category] = []
                self.category_manager.add_item(new_category)
                self._on_category_select(None)
    
    def _remove_category(self):
        """Remove selected category."""
        selected = self.category_manager.get_selected()
        
        if not selected:
            messagebox.showwarning(
                self._("NoSelectionWarningTitle"),
                self._("NoCategorySelectedMsg"),
                parent=self
            )
            return
        
        if messagebox.askyesno(
            self._("ConfirmRemoveTitle"),
            self._("ConfirmRemoveCategoryMsg", category=selected),
            icon='warning',
            parent=self
        ):
            del self.edited_config.categories[selected]
            self.category_manager.remove_selected()
            self._on_category_select(None)
    
    def _add_extension(self):
        """Add extension to selected category."""
        selected_category = self.category_manager.get_selected()
        
        if not selected_category:
            messagebox.showwarning(
                self._("NoSelectionWarningTitle"),
                self._("NoCategorySelectedMsg"),
                parent=self
            )
            return
        
        # Validate extension
        ext_input = self.extension_entry.get()
        is_valid, cleaned_ext, error_msg = ValidationHelper.validate_extension(ext_input, self._)
        
        if not is_valid:
            messagebox.showwarning(
                self._("InvalidExtensionWarningTitle"),
                error_msg,
                parent=self
            )
            return
        
        # Check if already exists
        if cleaned_ext in self.edited_config.categories[selected_category]:
            messagebox.showwarning(
                self._("DuplicateNameWarningTitle"),
                self._("DuplicateExtensionExistsInCategoryMsg",
                      default="Endung '{ext}' existiert bereits in Kat. '{category}'.",
                      ext=cleaned_ext, category=selected_category),
                parent=self
            )
        else:
            self.edited_config.categories[selected_category].append(cleaned_ext)
            self.extension_manager.add_item(cleaned_ext)
            self.extension_entry.delete(0, tk.END)
    
    def _remove_extension(self):
        """Remove selected extension."""
        selected_category = self.category_manager.get_selected()
        selected_extension = self.extension_manager.get_selected()
        
        if not selected_category or not selected_extension:
            messagebox.showwarning(
                self._("NoSelectionWarningTitle"),
                self._("NoCatOrExtSelectedMsg", default="Kategorie und Endung auswählen."),
                parent=self
            )
            return
        
        if messagebox.askyesno(
            self._("ConfirmRemoveTitle"),
            self._("ConfirmRemoveExtensionMsg",
                  ext=selected_extension, category=selected_category),
            parent=self
        ):
            self.edited_config.categories[selected_category].remove(selected_extension)
            self.extension_manager.remove_selected()
    
    def _add_exclusion(self):
        """Add extension exclusion."""
        ext_input = self.exclusion_entry.get()
        is_valid, cleaned_ext, error_msg = ValidationHelper.validate_extension(ext_input, self._)
        
        if not is_valid:
            messagebox.showwarning(
                self._("InvalidExtensionWarningTitle"),
                error_msg,
                parent=self
            )
            return
        
        if cleaned_ext not in self.edited_config.excluded_extensions:
            self.edited_config.excluded_extensions.add(cleaned_ext)
            self.exclusion_manager.add_item(cleaned_ext)
            self.exclusion_entry.delete(0, tk.END)
        else:
            messagebox.showinfo(
                self._("DuplicateNameWarningTitle"),
                self._("AlreadyExcludedExtensionMsg", ext=cleaned_ext),
                parent=self
            )
    
    def _remove_exclusion(self):
        """Remove selected exclusion."""
        selected = self.exclusion_manager.get_selected()
        
        if not selected:
            messagebox.showwarning(
                self._("NoSelectionWarningTitle"),
                self._("NoExclusionSelectedMsg"),
                parent=self
            )
            return
        
        if messagebox.askyesno(
            self._("ConfirmRemoveTitle"),
            self._("ConfirmRemoveExclusionMsg", ext=selected),
            parent=self
        ):
            self.edited_config.excluded_extensions.remove(selected)
            self.exclusion_manager.remove_selected()
    
    def _add_folder_exclusion(self):
        """Add folder exclusion."""
        folder_input = self.folder_entry.get()
        is_valid, cleaned_folder, error_msg = ValidationHelper.validate_folder_name(
            folder_input, self._
        )
        
        if not is_valid:
            messagebox.showwarning(
                self._("InvalidNameWarningTitle"),
                error_msg,
                parent=self
            )
            return
        
        if cleaned_folder not in self.edited_config.excluded_folders:
            self.edited_config.excluded_folders.add(cleaned_folder)
            self.folder_exclusion_manager.add_item(cleaned_folder)
            self.folder_entry.delete(0, tk.END)
        else:
            messagebox.showinfo(
                self._("DuplicateNameWarningTitle"),
                self._("AlreadyExcludedFolderMsg", folder=cleaned_folder),
                parent=self
            )
    
    def _remove_folder_exclusion(self):
        """Remove selected folder exclusion."""
        selected = self.folder_exclusion_manager.get_selected()
        
        if not selected:
            messagebox.showwarning(
                self._("NoSelectionWarningTitle"),
                self._("NoFolderExclusionSelectedMsg"),
                parent=self
            )
            return
        
        if messagebox.askyesno(
            self._("ConfirmRemoveTitle"),
            self._("ConfirmRemoveFolderExclusionMsg", folder=selected),
            parent=self
        ):
            self.edited_config.excluded_folders.remove(selected)
            self.folder_exclusion_manager.remove_selected()
    
    def save_changes(self):
        """Save configuration changes."""
        with safe_gui_operation(self, "SaveConfig", self._):
            if self.config_manager.save_config(self.edited_config):
                self.destroy()
    
    def cancel_changes(self):
        """Cancel without saving."""
        self.destroy()