import re


def convert_headings(text):
    levels = {'=': '#', '==': '##', '===': '###', '====': '####'}
    for wikicode, markdown in levels.items():
        text = text.replace(wikicode, markdown).replace(wikicode[::-1], "")
    return text


#def convert_headings(text):
#    # Regex, die die Wikitext-Überschriften erkennt und gruppiert
#    pattern = r'(=+)([^=]+)\1'

    # Funktion, die das Regex-Match nimmt und in Markdown-Format konvertiert
#    def replace_with_markdown(match):
#        level = len(match.group(1))  # Bestimmt die Tiefe der Überschrift basierend auf der Anzahl der '='
#        heading_text = match.group(2).strip()  # Entfernt zusätzliche Leerzeichen um den Text
#        return f"{'#' * level} {heading_text}"

    # Ersetzt alle Überschriften im gegebenen Text
#    return re.sub(pattern, replace_with_markdown, text)


def convert_bold_italic(text):
    text = text.replace("'''", '**')  # Fett in Markdown
    text = text.replace("''", '*')    # Kursiv in Markdown
    return text


def convert_links(text):
    pattern = r'\[\[(.*?)\|(.*?)\]\]'
    replacement = r'[\2](\1)'
    text = re.sub(pattern, replacement, text)
    return text


def wiki_to_markdown(text):
    text = convert_headings(text)
    text = convert_bold_italic(text)
    text = convert_links(text)
    return text
