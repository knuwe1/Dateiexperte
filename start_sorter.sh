#!/usr/bin/env bash

# Definiere den Pfad zur virtuellen Umgebung und zum Skript
VENV_DIR=".kenv"
SCRIPT_NAME="main.py"
ACTIVATE_SCRIPT="$VENV_DIR/bin/activate" # Pfad für Linux/macOS

# Prüfe, ob das Aktivierungsskript existiert
if [ ! -f "$ACTIVATE_SCRIPT" ]; then
    echo "Fehler: Aktivierungsskript '$ACTIVATE_SCRIPT' nicht gefunden."
    echo "Stelle sicher, dass die virtuelle Umgebung in '$VENV_DIR' existiert und korrekt erstellt wurde."
    exit 1
fi

# Prüfe, ob das Python-Skript existiert
if [ ! -f "$SCRIPT_NAME" ]; then
    echo "Fehler: Python-Skript '$SCRIPT_NAME' nicht gefunden."
    exit 1
fi

echo "Aktiviere virtuelle Umgebung: $VENV_DIR"
# Aktiviere die virtuelle Umgebung
source "$ACTIVATE_SCRIPT"

echo "Starte Python-Skript: $SCRIPT_NAME"
# Führe das Python-Skript aus
python "$SCRIPT_NAME"

# Optional: Deaktiviere die virtuelle Umgebung nach Ausführung
# Die Deaktivierung geschieht meist automatisch beim Beenden des Skripts,
# kann aber explizit aufgerufen werden.
# deactivate

echo "Skript '$SCRIPT_NAME' beendet."

exit 0