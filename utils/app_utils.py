import re

import wikipedia
import mwparserfromhell
import utils.wiki_utils as wiki_utils
from utils.wikimdparser import wiki_to_markdown
from utils.filecache import cache_with_disk
from utils.snowflake_helper import SnowflakeHelper


def escape_markdown(text):
    # Escape Dollarzeichen und andere spezielle Markdown-Zeichen
    text = text.replace("$", "\$")
    # Ersetze \n durch zwei Leerzeichen gefolgt von \n für korrekte Markdown Zeilenumbrüche
    text = text.replace("\n", "  \n  \n")
    text = wiki_to_markdown(text)
    return text


@cache_with_disk()
def wiki_search(wiki_query):
    try:
        # Hole die Seite von Wikipedia
        page = wiki_utils.search(wiki_query)
        page = wiki_utils.page(title=page[0], auto_suggest=False, preload=True)

        return page
    except wikipedia.exceptions.DisambiguationError as e:
        # Behandlung von Mehrdeutigkeiten, indem die verschiedenen Optionen aufgelistet werden
        return f"Mehrdeutiger Begriff, bitte präzisiere. Einige Möglichkeiten: {', '.join(e.options[:5])}"
    except wikipedia.exceptions.PageError as pe:
        # Kein Artikel gefunden
        print(pe)
        return "Kein Artikel gefunden."


def get_sections(extract, read_to_section, target_language, image_html=None):
    wikicode = mwparserfromhell.parse(extract)
    print(f"Section to read: {read_to_section}")
    print(len(wikicode.nodes))
    sections = ''
    section_counter = 0
    for node in wikicode.nodes:
        new_section = escape_markdown(node)
        print(new_section)
        if new_section and len(new_section.strip()) > 0:
            if section_counter == 0 and image_html:
                sections += image_html

            if target_language in ["de", "fr", "es", "it"]:
                sections += get_translated_section(new_section, target_language)
            else:
                sections += new_section

            if new_section.startswith("#"):
                sections += "\n"
                continue

            section_counter += 1
            if section_counter >= read_to_section:
                break

    return sections


@cache_with_disk()
def get_translated_section(section, target_language):

    pattern = r'#+\s.*?\s#+'
    segments = re.findall(pattern, section, flags=re.MULTILINE)
    if segments and len(segments) > 0:
        section = segments[0]
        print(section)
        clean_section = segments[0].strip("# ").strip()
        print(clean_section)
        translated_section = translate(clean_section, target_language, new_line=False)
        translated_section = translated_section.strip()
        print(translated_section)
        translated_section = section.replace(clean_section, translated_section)
        print(f"-{translated_section}-")
        translated_section = f"\n{translated_section}\n"
    else:
        translated_section = translate(section, target_language) + "\n\n"

    return translated_section


def translate(text, target_language, new_line=True):
    snowflake_helper = SnowflakeHelper()

    # TODO Dirty hack instead of chunking the text. Depending that wiki text is well formatted ;-)
    text_parts = text.split("\n")
    translated_text = ""
    for index, text_part in enumerate(text_parts):
        if len(text_part.strip()) > 0:
            print("Translation section_part ", index)
            print(text_part)
            translated_text += snowflake_helper.translate(text_part, target_language)
            if new_line:
                translated_text += "\n\n"

    return translated_text


def summarize(text, new_line=True):
    snowflake_helper = SnowflakeHelper()
    summary = snowflake_helper.summarize(text)
    if new_line:
        summary += "\n\n"
    return summary


@cache_with_disk()
def get_strong_summary(summary, image_html, target_language):
    strong_summary = summarize(summary)
    strong_summary = image_html + escape_markdown(strong_summary)
    return strong_summary


@cache_with_disk()
def get_translation(text, target_language):
    snowflake_helper = SnowflakeHelper()
    return snowflake_helper.translate(text, target_language)


@cache_with_disk()
def get_summary(extract, image_html, target_language, max_section_summarized=10):
    wikicode = mwparserfromhell.parse(extract)

    print("Node to be summarized: ", len(wikicode.nodes))
    summary = ''
    current_section = ''

    section_counter = 0
    for node in wikicode.nodes:
        new_section = escape_markdown(node)
        if new_section and len(new_section.strip()) > 0:
            current_section += new_section

            if new_section.startswith("#"):
                continue

            current_section = summarize(current_section)

            if target_language in ["de", "fr", "es", "it"]:
                current_section = translate(current_section, target_language)

            summary += current_section

        section_counter += 1
        current_section = ''

        if section_counter >= max_section_summarized:
            break

    summary = image_html + escape_markdown(summary)
    return summary


def get_article_image(image_filename):
    image_html = ""

    if image_filename:
        image_url = wiki_utils.get_image_url(image_filename)
        # Erstelle HTML-Code für das Bild mit Textfluss
        image_html = f'<div style="float: left; margin-right: 15px; margin-top: 8px"><img src="{image_url}" alt="Bild" style="max-height: 200px;"></div>'

    return image_html
