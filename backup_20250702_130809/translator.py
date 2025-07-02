# -*- coding: utf-8 -*-
"""
Translator Klasse für Dateiexperte v1.11+
Verwaltet das Laden und Abrufen von Übersetzungen aus JSON-Dateien.
"""

import json
import os
import locale # Für Systemspracheerkennung

class Translator:
    """Verwaltet das Laden und Abrufen von Übersetzungen aus JSON-Dateien."""
    # Korrekte __init__ Signatur mit language_code und default_lang
    def __init__(self, locales_dir='locales', language_code='en', default_lang='en'):
        """
        Initialisiert den Translator.

        Args:
            locales_dir (str): Verzeichnis (relativ zum Skript) mit den Sprachdateien (z.B. de.json).
            language_code (str): Zuerst zu ladender Sprachcode (z.B. 'de', 'en').
            default_lang (str): Sprache, die als Fallback geladen wird.
        """
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            base_dir = os.getcwd()
        self.locales_dir = os.path.join(base_dir, locales_dir)
        self.translations = {}
        self.language = default_lang # Start mit Default
        self.default_lang = default_lang

        # Versuche direkt die gewünschte Sprache zu laden
        self.load_language(language_code)

    def load_language(self, lang_code):
        """Lädt die Übersetzungen für den gegebenen Sprachcode."""
        self.language = lang_code
        file_path = os.path.join(self.locales_dir, f"{self.language}.json")
        fallback_path = os.path.join(self.locales_dir, f"{self.default_lang}.json")
        loaded_successfully = False

        try:
            print(f"INFO: Versuche Sprachdatei zu laden: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            print(f"INFO: Sprache '{self.language}' erfolgreich geladen.")
            loaded_successfully = True
        except FileNotFoundError:
            print(f"WARNUNG: Sprachdatei '{file_path}' nicht gefunden.")
            if self.language != self.default_lang:
                print(f"INFO: Versuche Fallback-Sprache '{self.default_lang}' zu laden...")
                try:
                    with open(fallback_path, 'r', encoding='utf-8') as f:
                        self.translations = json.load(f)
                    print(f"INFO: Fallback-Sprache '{self.default_lang}' erfolgreich geladen.")
                    self.language = self.default_lang
                    loaded_successfully = True
                except FileNotFoundError:
                    print(f"FEHLER: Fallback-Sprachdatei '{fallback_path}' auch nicht gefunden! Keine Übersetzungen aktiv.")
                    self.translations = {}
                except json.JSONDecodeError as e_fb:
                    print(f"FEHLER: Fallback-Sprachdatei '{fallback_path}' ungültiges JSON: {e_fb}")
                    self.translations = {}
                except Exception as e_fb_other:
                     print(f"FEHLER: Unerwarteter Fehler beim Laden Fallback: {e_fb_other}")
                     self.translations = {}
            else:
                print(f"FEHLER: Standard-Sprachdatei '{fallback_path}' nicht gefunden! Keine Übersetzungen aktiv.")
                self.translations = {}
        except json.JSONDecodeError as e:
            print(f"FEHLER: Sprachdatei '{file_path}' ungültiges JSON: {e}")
            self.translations = {}
        except Exception as e_other:
             print(f"FEHLER: Unerwarteter Fehler Laden Sprache '{self.language}': {e_other}")
             self.translations = {}

        if not loaded_successfully:
             print("WARNUNG: Keine gültige Sprachdatei geladen. Übersetzungsfunktion gibt Schlüssel zurück.")


    def get_string(self, key, default=None, **kwargs):
        """
        Gibt den übersetzten String für einen Schlüssel zurück.
        Fügt optional Argumente in den String ein (mittels .format()).
        """
        fallback_value = default if default is not None else key
        translated = self.translations.get(key, fallback_value)

        if not self.translations and key != fallback_value:
             if default is not None: translated = default

        if kwargs:
            try:
                return translated.format(**kwargs)
            except KeyError as e:
                print(f"WARNUNG: Fehlender Platzhalter {e} für Schlüssel '{key}' in Sprache '{self.language}'. Original: '{translated}'")
                return translated
            except Exception as e_fmt:
                 print(f"FEHLER Formatierung Schlüssel '{key}' in Sprache '{self.language}': {e_fmt}. Original: '{translated}'")
                 return translated
        else:
            return translated