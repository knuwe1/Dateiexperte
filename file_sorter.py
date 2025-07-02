# -*- coding: utf-8 -*-
"""
File sorting logic extracted from main application.
Handles file categorization, copying, and moving operations.
"""

import os
import shutil
from typing import List, Tuple, Callable, Optional
from dataclasses import dataclass
from config_models import SorterConfig


@dataclass
class SortResult:
    """Result of a file sorting operation."""
    processed: int = 0
    skipped: int = 0
    errors: int = 0
    total: int = 0


@dataclass
class FileOperation:
    """Represents a single file operation."""
    source_path: str
    target_path: str
    category: str
    operation_type: str  # 'copy' or 'move'


class FileSorter:
    """Handles file sorting operations."""
    
    def __init__(self, config: SorterConfig, logger: Optional[Callable] = None):
        self.config = config
        self.logger = logger or print
        self.extension_map = config.build_extension_map()
    
    def discover_files(self, source_dir: str, target_dir: str) -> List[str]:
        """Discover all files to be sorted."""
        all_files = []
        target_abs = os.path.abspath(target_dir)
        
        self.logger("Suche Dateien...")
        
        for root, dirs, files in os.walk(source_dir, topdown=True):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if d.lower() not in self.config.excluded_folders]
            
            # Skip if we're inside the target directory
            root_abs = os.path.abspath(root)
            if root_abs.startswith(target_abs):
                continue
            
            # Add all files from this directory
            for filename in files:
                all_files.append(os.path.join(root, filename))
        
        self.logger(f"{len(all_files)} Dateien gefunden.")
        return all_files
    
    def categorize_file(self, file_path: str) -> Tuple[str, str]:
        """
        Categorize a file based on its extension.
        Returns: (category_name, relative_target_path)
        """
        filename = os.path.basename(file_path)
        _, extension = os.path.splitext(filename)
        extension_lower = extension.lower() if extension else ''
        
        # Check if extension is excluded
        if extension_lower in self.config.excluded_extensions:
            return None, None
        
        # Get category for this extension
        category_name = self.extension_map.get(
            extension_lower, 
            self.config.default_category
        )
        
        # Build target path
        if category_name != self.config.default_category and extension_lower:
            # Create subfolder for specific file type
            type_folder = extension_lower.lstrip('.')
            if type_folder:
                relative_path = os.path.join(category_name, type_folder)
            else:
                relative_path = category_name
        else:
            relative_path = category_name
        
        return category_name, relative_path
    
    def get_unique_target_path(self, target_dir: str, filename: str) -> str:
        """Get a unique target path, handling duplicates."""
        target_path = os.path.join(target_dir, filename)
        
        if not os.path.exists(target_path):
            return target_path
        
        # Handle duplicates
        name, ext = os.path.splitext(filename)
        counter = 1
        
        while os.path.exists(target_path):
            target_path = os.path.join(target_dir, f"{name}({counter}){ext}")
            counter += 1
        
        return target_path
    
    def process_file(self, file_op: FileOperation) -> bool:
        """
        Process a single file operation.
        Returns True if successful, False otherwise.
        """
        try:
            # Create target directory if needed
            target_dir = os.path.dirname(file_op.target_path)
            if not os.path.isdir(target_dir):
                os.makedirs(target_dir, exist_ok=True)
            
            # Perform the operation
            if file_op.operation_type == "copy":
                shutil.copy2(file_op.source_path, file_op.target_path)
            elif file_op.operation_type == "move":
                shutil.move(file_op.source_path, file_op.target_path)
            else:
                raise ValueError(f"Unknown operation type: {file_op.operation_type}")
            
            return True
            
        except OSError as e:
            self.logger(f"FEHLER bei {file_op.operation_type}: {os.path.basename(file_op.source_path)} -> {file_op.category}: {e}")
            return False
        except Exception as e:
            self.logger(f"Unerwarteter Fehler: {os.path.basename(file_op.source_path)}: {e}")
            return False
    
    def sort_files(self, source_dir: str, target_dir: str, operation: str,
                   progress_callback: Optional[Callable[[int], None]] = None) -> SortResult:
        """
        Sort files from source to target directory.
        
        Args:
            source_dir: Source directory path
            target_dir: Target directory path
            operation: 'copy' or 'move'
            progress_callback: Optional callback for progress updates
            
        Returns:
            SortResult with statistics
        """
        result = SortResult()
        
        # Discover files
        all_files = self.discover_files(source_dir, target_dir)
        result.total = len(all_files)
        
        if result.total == 0:
            self.logger("Keine Dateien zum Sortieren gefunden.")
            return result
        
        # Process each file
        for i, source_path in enumerate(all_files):
            filename = os.path.basename(source_path)
            
            # Categorize file
            category, relative_path = self.categorize_file(source_path)
            
            if category is None:
                # File was excluded
                result.skipped += 1
            else:
                # Build target path
                category_dir = os.path.join(target_dir, relative_path)
                target_path = self.get_unique_target_path(category_dir, filename)
                
                # Check if we need to rename
                if os.path.basename(target_path) != filename:
                    self.logger(f"Datei existiert bereits, benenne um: {os.path.basename(target_path)} -> {relative_path}")
                
                # Create file operation
                file_op = FileOperation(
                    source_path=source_path,
                    target_path=target_path,
                    category=relative_path,
                    operation_type=operation
                )
                
                # Process the file
                if self.process_file(file_op):
                    result.processed += 1
                else:
                    result.errors += 1
            
            # Report progress
            if progress_callback:
                progress_callback(i + 1)
        
        return result
    
    def validate_directories(self, source_dir: str, target_dir: str) -> Optional[str]:
        """
        Validate source and target directories.
        Returns error message if validation fails, None if OK.
        """
        # Check source directory
        if not source_dir or not os.path.isdir(source_dir):
            return "Quellordner ungültig oder nicht vorhanden."
        
        # Check target directory
        if not target_dir:
            return "Zielordner nicht angegeben."
        
        # Resolve absolute paths
        try:
            source_abs = os.path.abspath(source_dir)
            target_abs = os.path.abspath(target_dir)
            
            # Check if target is inside source
            if source_abs == target_abs or target_abs.startswith(source_abs + os.path.sep):
                return "Zielordner darf nicht innerhalb des Quellordners liegen."
                
        except OSError as e:
            return f"Fehler bei Pfadprüfung: {e}"
        
        return None