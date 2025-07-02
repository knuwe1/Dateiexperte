# -*- coding: utf-8 -*-
"""
Configuration data models for Dateiexperte.
Provides type-safe configuration management using dataclasses.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set
import json
import os


@dataclass
class SorterConfig:
    """Main configuration data structure for file sorting."""
    categories: Dict[str, List[str]] = field(default_factory=dict)
    default_category: str = "_Unsortiert"
    excluded_extensions: Set[str] = field(default_factory=set)
    excluded_folders: Set[str] = field(default_factory=set)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SorterConfig':
        """Create SorterConfig from dictionary."""
        return cls(
            categories=data.get("Kategorien", {}),
            default_category=data.get("StandardKategorie", "_Unsortiert"),
            excluded_extensions=set(data.get("AusgeschlosseneEndungen", [])),
            excluded_folders=set(data.get("AusgeschlosseneOrdner", []))
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "Kategorien": self.categories,
            "StandardKategorie": self.default_category,
            "AusgeschlosseneEndungen": sorted(list(self.excluded_extensions)),
            "AusgeschlosseneOrdner": sorted(list(self.excluded_folders))
        }
    
    def build_extension_map(self) -> Dict[str, str]:
        """Build a mapping from extensions to categories."""
        extension_map = {}
        for category, extensions in self.categories.items():
            for ext in extensions:
                if isinstance(ext, str) and ext.startswith('.'):
                    extension_map[ext.lower()] = category
        return extension_map


class ConfigValidator:
    """Validates and sanitizes configuration data."""
    
    @staticmethod
    def validate_categories(categories: dict, logger=None) -> Dict[str, List[str]]:
        """Validate category structure and extensions."""
        validated = {}
        
        if not isinstance(categories, dict):
            if logger:
                logger("FEHLER: 'Kategorien' kein Dictionary.")
            return {}
        
        for category, extensions in categories.items():
            if not isinstance(extensions, list):
                if logger:
                    logger(f"Warnung: Ungültiges Format für Extensions in Kat. '{category}'")
                continue
                
            valid_extensions = []
            for ext in extensions:
                if isinstance(ext, str) and ext.startswith('.') and len(ext) > 1:
                    valid_extensions.append(ext.lower())
                elif logger:
                    logger(f"Warnung: Ignoriere ungültige Endung '{ext}' in Kat '{category}'.")
            
            if valid_extensions:
                validated[category] = valid_extensions
                
        return validated
    
    @staticmethod
    def validate_extensions(extensions: list, logger=None) -> Set[str]:
        """Validate file extensions."""
        validated = set()
        
        if not isinstance(extensions, list):
            if logger:
                logger("Warnung: 'AusgeschlosseneEndungen' keine Liste.")
            return set()
        
        for ext in extensions:
            if isinstance(ext, str) and ext.startswith('.') and len(ext) > 1:
                validated.add(ext.lower())
            elif logger:
                logger(f"Warnung: Ignoriere ungültige Ausschlusserweiterung '{ext}'.")
                
        return validated
    
    @staticmethod
    def validate_folders(folders: list, logger=None) -> Set[str]:
        """Validate folder names."""
        validated = set()
        
        if not isinstance(folders, list):
            if logger:
                logger("Warnung: 'AusgeschlosseneOrdner' keine Liste.")
            return set()
        
        for folder in folders:
            if isinstance(folder, str) and folder.strip():
                validated.add(folder.strip().lower())
            elif logger:
                logger(f"Warnung: Ignoriere ungültigen Ordnerausschluss '{folder}'.")
                
        return validated


class ConfigManager:
    """Manages loading and saving configuration."""
    
    def __init__(self, config_file: str, logger=None):
        self.config_file = config_file
        self.logger = logger or print
        self.validator = ConfigValidator()
    
    def load_config(self) -> SorterConfig:
        """Load configuration from file."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return self._validate_config_data(data)
        except FileNotFoundError:
            self.logger(f"'{os.path.basename(self.config_file)}' nicht gefunden. Erstelle Standard...")
            return self.create_default_config()
        except json.JSONDecodeError as e:
            self.logger(f"FEHLER Lesen JSON: {e}")
            return SorterConfig()
        except Exception as e:
            self.logger(f"FEHLER Laden Config: {e}")
            return SorterConfig()
    
    def save_config(self, config: SorterConfig) -> bool:
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config.to_dict(), f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            self.logger(f"FEHLER Speichern Config: {e}")
            return False
    
    def create_default_config(self) -> SorterConfig:
        """Create and save default configuration."""
        default_config = SorterConfig(
            categories={
                "Bilder": [".jpg", ".png", ".gif", ".bmp", ".svg", ".ico", ".webp"],
                "Dokumente": [".pdf", ".doc", ".docx", ".txt", ".odt", ".rtf"],
                "Musik": [".mp3", ".wav", ".flac", ".ogg", ".m4a", ".wma"],
                "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv"],
                "Archive": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"]
            },
            default_category="_Unsortiert",
            excluded_extensions={".tmp", ".ini", ".log", ".temp"},
            excluded_folders={"temp", ".git", "__pycache__", "node_modules"}
        )
        
        if self.save_config(default_config):
            self.logger(f"Standard-Config '{os.path.basename(self.config_file)}' erstellt.")
            return default_config
        else:
            return SorterConfig()
    
    def _validate_config_data(self, data: dict) -> SorterConfig:
        """Validate loaded configuration data."""
        if not isinstance(data, dict):
            self.logger("Konfigformat ungültig. Verwende Defaults.")
            return SorterConfig()
        
        # Validate categories
        categories = self.validator.validate_categories(
            data.get("Kategorien", {}), 
            self.logger
        )
        
        # Validate default category
        default_category = data.get("StandardKategorie", "_Unsortiert")
        if not isinstance(default_category, str) or not default_category.strip():
            default_category = "_Unsortiert"
            self.logger("Warnung: StandardKategorie leer, verwende '_Unsortiert'.")
        
        # Validate exclusions
        excluded_extensions = self.validator.validate_extensions(
            data.get("AusgeschlosseneEndungen", []),
            self.logger
        )
        
        excluded_folders = self.validator.validate_folders(
            data.get("AusgeschlosseneOrdner", []),
            self.logger
        )
        
        return SorterConfig(
            categories=categories,
            default_category=default_category,
            excluded_extensions=excluded_extensions,
            excluded_folders=excluded_folders
        )