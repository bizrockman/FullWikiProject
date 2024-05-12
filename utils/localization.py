import os

# Dictionary, das alle Übersetzungen speichert
translations = {}

def load_translations(directory):
    """Lädt alle Übersetzungen aus Dateien im angegebenen Verzeichnis."""
    for filename in os.listdir(directory):
        if filename.endswith('.txt'):
            lang_code = filename.split('.')[0]
            with open(os.path.join(directory, filename), 'r', encoding='utf-8') as f:
                translations[lang_code] = {}
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        translations[lang_code][key] = value


def set_language(lang_code):
    """Setzt die aktuelle Sprache für die Übersetzungen."""
    global current_language
    current_language = lang_code


def _(text):
    """Gibt die Übersetzung für den angegebenen Text zurück."""
    return translations.get(current_language, {}).get(text, text)