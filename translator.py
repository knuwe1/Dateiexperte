# -*- coding: utf-8 -*-
"""
Enhanced Translator class with improved error handling and structure.
"""

import json
import os
import locale
from typing import Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TranslationConfig:
    """Configuration for the translator."""
    locales_dir: str = 'locales'
    language_code: str = 'en'
    default_lang: str = 'en'
    fallback_to_key: bool = True


class TranslationError(Exception):
    """Custom exception for translation errors."""
    pass


class Translator:
    """Enhanced translator with better error handling and caching."""
    
    def __init__(self, locales_dir='locales', language_code='en', default_lang='en', config: Optional[TranslationConfig] = None):
        """
        Initialize the translator with configuration.
        
        Args:
            locales_dir: Directory containing locale files (backward compatibility)
            language_code: Language code to load (backward compatibility)
            default_lang: Default language (backward compatibility)
            config: Translation configuration object (new way)
        """
        # Backward compatibility: if config not provided, create from args
        if config is None:
            config = TranslationConfig(
                locales_dir=locales_dir,
                language_code=language_code,
                default_lang=default_lang
            )
        
        self.config = config
        self.translations: Dict[str, Any] = {}
        self.language = self.config.default_lang
        self._base_dir = self._get_base_directory()
        self._translation_cache: Dict[str, str] = {}
        
        # Load initial language
        self.load_language(self.config.language_code)
    
    def _get_base_directory(self) -> Path:
        """Get the base directory for locale files."""
        try:
            return Path(os.path.dirname(os.path.abspath(__file__)))
        except NameError:
            return Path.cwd()
    
    def _get_locale_path(self, lang_code: str) -> Path:
        """Get the full path to a locale file."""
        return self._base_dir / self.config.locales_dir / f"{lang_code}.json"
    
    def _load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Load and parse a JSON file with proper error handling.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            Parsed JSON data
            
        Raises:
            TranslationError: If file cannot be loaded or parsed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise TranslationError(f"Translation file not found: {file_path}")
        except json.JSONDecodeError as e:
            raise TranslationError(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            raise TranslationError(f"Error loading {file_path}: {e}")
    
    def load_language(self, lang_code: str) -> bool:
        """
        Load translations for the specified language.
        
        Args:
            lang_code: Language code to load
            
        Returns:
            True if successfully loaded, False otherwise
        """
        self._translation_cache.clear()  # Clear cache when changing language
        
        # Try to load requested language
        try:
            file_path = self._get_locale_path(lang_code)
            self.translations = self._load_json_file(file_path)
            self.language = lang_code
            print(f"INFO: Language '{lang_code}' successfully loaded.")
            return True
            
        except TranslationError as e:
            print(f"WARNING: {e}")
            
            # Try fallback language if different
            if lang_code != self.config.default_lang:
                try:
                    return self._load_fallback_language()
                except TranslationError as fallback_error:
                    print(f"ERROR: {fallback_error}")
            
            # No translations available
            self.translations = {}
            print("WARNING: No translations loaded. Using keys as fallback.")
            return False
    
    def _load_fallback_language(self) -> bool:
        """
        Load the fallback language.
        
        Returns:
            True if successfully loaded
            
        Raises:
            TranslationError: If fallback cannot be loaded
        """
        print(f"INFO: Attempting to load fallback language '{self.config.default_lang}'...")
        fallback_path = self._get_locale_path(self.config.default_lang)
        self.translations = self._load_json_file(fallback_path)
        self.language = self.config.default_lang
        print(f"INFO: Fallback language '{self.config.default_lang}' loaded.")
        return True
    
    def get_string(self, key: str, default: Optional[str] = None, **kwargs) -> str:
        """
        Get a translated string with optional formatting.
        
        Args:
            key: Translation key
            default: Default value if key not found
            **kwargs: Format arguments
            
        Returns:
            Translated and formatted string
        """
        # Check cache first
        cache_key = f"{key}:{repr(sorted(kwargs.items()))}" if kwargs else key
        if cache_key in self._translation_cache:
            return self._translation_cache[cache_key]
        
        # Get base translation
        if self.config.fallback_to_key:
            fallback_value = default if default is not None else key
        else:
            fallback_value = default or ""
        
        translated = self.translations.get(key, fallback_value)
        
        # Apply formatting if needed
        if kwargs:
            try:
                result = translated.format(**kwargs)
                self._translation_cache[cache_key] = result
                return result
            except KeyError as e:
                print(f"WARNING: Missing placeholder {e} for key '{key}' in '{self.language}'")
                return translated
            except Exception as e:
                print(f"ERROR: Format error for key '{key}': {e}")
                return translated
        
        self._translation_cache[cache_key] = translated
        return translated
    
    def get_available_languages(self) -> list[str]:
        """
        Get list of available language codes.
        
        Returns:
            List of language codes for which translation files exist
        """
        locales_path = self._base_dir / self.config.locales_dir
        
        if not locales_path.exists():
            return []
        
        languages = []
        for file_path in locales_path.glob("*.json"):
            lang_code = file_path.stem
            languages.append(lang_code)
        
        return sorted(languages)
    
    def reload_current_language(self) -> bool:
        """
        Reload the current language (useful for development).
        
        Returns:
            True if successfully reloaded
        """
        return self.load_language(self.language)
    
    @staticmethod
    def detect_system_language() -> str:
        """
        Detect the system language.
        
        Returns:
            Language code (e.g., 'en', 'de')
        """
        try:
            # Try to get locale
            system_locale = locale.getlocale()[0]
            if system_locale:
                return system_locale.split('_')[0].lower()
        except Exception as e:
            print(f"WARNING: Could not detect system language: {e}")
        
        return 'en'  # Default fallback
    
    def change_language(self, lang_code: str) -> bool:
        """
        Change to a different language.
        
        Args:
            lang_code: Language code to switch to
            
        Returns:
            True if successfully changed
        """
        if lang_code == self.language:
            return True  # Already using this language
        
        # Save current state in case we need to revert
        old_language = self.language
        old_translations = self.translations.copy()
        
        if self.load_language(lang_code):
            return True
        else:
            # Revert to previous state
            self.language = old_language
            self.translations = old_translations
            return False


def create_translator(language_code: Optional[str] = None,
                     supported_languages: Optional[list[str]] = None) -> Translator:
    """
    Factory function to create a configured translator.
    
    Args:
        language_code: Specific language to use (None for auto-detect)
        supported_languages: List of supported languages
        
    Returns:
        Configured Translator instance
    """
    if language_code is None:
        language_code = Translator.detect_system_language()
    
    if supported_languages and language_code not in supported_languages:
        language_code = 'en'  # Default to English if not supported
    
    config = TranslationConfig(
        language_code=language_code,
        default_lang='en'
    )
    
    return Translator(config)