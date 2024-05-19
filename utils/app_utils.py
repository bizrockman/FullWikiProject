import re
import time

import wikipedia
import mwparserfromhell
import utils.wiki_utils as wiki_utils
from utils.wikimdparser import wiki_to_markdown
from utils.filecache import cache_with_disk
from utils.snowflake_helper import SnowflakeHelper
from utils.localization import _


supported_languages = {
    "de": "German",
    "en": "English",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian"
}

def escape_markdown(text):
    # Escape Dollarzeichen und andere spezielle Markdown-Zeichen
    text = text.replace("$", "\$")
    # Ersetze \n durch zwei Leerzeichen gefolgt von \n für korrekte Markdown Zeilenumbrüche
    text = text.replace("\n", "  \n  \n")
    text = wiki_to_markdown(text)
    return text


@cache_with_disk()
def wiki_search(wiki_query, wikipedia_language="en"):
    try:
        # Hole die Seite von Wikipedia
        wiki_utils.set_lang(wikipedia_language)

        search_results = wiki_utils.search(wiki_query)
        if len(search_results) > 0:
            print(search_results)
            try:
                page = wiki_utils.page(title=search_results[0], auto_suggest=False, preload=True)
            except wikipedia.exceptions.DisambiguationError as de:
                print("Disambiguation Error: Trying with search")
                page = wiki_search(search_results[1], wikipedia_language)

            return page
        return None
    except wikipedia.exceptions.DisambiguationError as e:
        # Behandlung von Mehrdeutigkeiten, indem die verschiedenen Optionen aufgelistet werden
        return f"Mehrdeutiger Begriff, bitte präzisiere. Einige Möglichkeiten: {', '.join(e.options[:5])}"
    except wikipedia.exceptions.PageError as pe:
        # Kein Artikel gefunden
        print(pe)
        return "Kein Artikel gefunden."


@cache_with_disk()
def get_section_headlines(extract, skip_translation=False):
    parsed = mwparserfromhell.parse(extract)
    section_headlines = parsed.filter_headings()
    headlines = ''
    for section in section_headlines:
        if skip_translation:
            translated_section = section.title.strip()
        else:
            translated_section = translate(section.title.strip(), 'en', new_line=False, is_search_term=True)
        if section.level == 2:
            headlines += "## " + translated_section + "\n"
        elif section.level == 3:
            headlines += "### " + translated_section + "\n"
    return headlines


def improve_outline(english_outline, foreign_outline):
    snowflake_helper = SnowflakeHelper()
    improved_outline = snowflake_helper.improve_article_outline(english_outline, foreign_outline)
    return improved_outline


def polish_outline(outline, wiki_query):
    snowflake_helper = SnowflakeHelper()
    polish_outline = snowflake_helper.polish_outline(outline, wiki_query)
    return polish_outline


def merge_knowledge(master_section, compare_section):
    snowflake_helper = SnowflakeHelper()
    combined_sections = snowflake_helper.combine_sections(master_section, compare_section)
    return combined_sections


@cache_with_disk()
def rewrite_section(combined_section, wiki_query=None):
    snowflake_helper = SnowflakeHelper()
    rewritten_section = snowflake_helper.rewrite_article_section(combined_section, wiki_query)
    return rewritten_section


@cache_with_disk()
def extract_keyfacts(combined_section, wiki_query):
    snowflake_helper = SnowflakeHelper()
    rewritten_section = snowflake_helper.extract_keyfacts(combined_section, wiki_query)
    return rewritten_section


def _get_wikipage_from_language(search_term, language_code):
    search_term = translate(search_term, language_code, new_line=False, is_search_term=True)
    wiki_page = wiki_search(search_term, language_code)
    return wiki_page


def _get_wikipage_leading_abstract(extract):
    wikicode = mwparserfromhell.parse(extract)
    abstract = ''
    for node in wikicode.nodes:
        if isinstance(node, mwparserfromhell.nodes.Heading):
            break
        abstract += escape_markdown(node)

    return abstract


def _get_translated_abstract(log_area, urls, en_search_term, language_code):
    log_area.text(_(f"Getting the {supported_languages[language_code]} Wikipedia article ..."))
    try:
        wiki_page = _get_wikipage_from_language(en_search_term, language_code)
        urls[language_code] = wiki_page.url
        abstract = _get_wikipage_leading_abstract(wiki_page.extract)
        log_area.text(_(f"Translate {supported_languages[language_code]} Wikipedia abstract to english ..."))
        abstract_in_en = translate(abstract, 'en')
        keyfacts_in_en = extract_keyfacts(abstract_in_en, en_search_term)
        print("-" * 50)
        print(keyfacts_in_en)
        print("-" * 50)
    except Exception as e:
        print(e)
        log_area.text(_(f"ERROR: Could not get the {supported_languages[language_code]} Wikipedia article ..."))
        time.sleep(3)
        keyfacts_in_en = ''
    return keyfacts_in_en


def get_combined_knowledge_sections(log_area, en_wiki_page, en_search_term, target_language,
                                    read_to_section, image_html=None):
    # if read_to_section == 1 - Only combine the first section
    urls = {"en": en_wiki_page.url}
    en_abstract = _get_wikipage_leading_abstract(en_wiki_page.extract)

    translated_de_abstract_in_en = _get_translated_abstract(log_area, urls, en_search_term, 'de')
    translated_fr_abstract_in_en = _get_translated_abstract(log_area, urls, en_search_term, 'fr')
    translated_es_abstract_in_en = _get_translated_abstract(log_area, urls, en_search_term, 'es')
    translated_it_abstract_in_en = _get_translated_abstract(log_area, urls, en_search_term, 'it')

    combined_abstract = (en_abstract + translated_de_abstract_in_en + translated_fr_abstract_in_en
                         + translated_es_abstract_in_en + translated_it_abstract_in_en)
    log_area.text(_(f"Combining the knowledge from all languages ..."))
    combined_section = rewrite_section(combined_abstract, en_search_term)

    if target_language != 'en':
        log_area.text(_(f"Translate the combined knowledge to {supported_languages[target_language]} ..."))
        combined_section = get_translated_section(combined_section, target_language)

    combined_section = escape_markdown(combined_section)

    if image_html:
        combined_section = image_html + combined_section

    return urls, combined_section

   # OPTIONAL code if read_to_section > 1 the outline and article needs to be created from scratch section by section
   #    en_outline = get_section_headlines(en_wiki_page.extract, skip_translation=True)
   #     log_area.text(_(f"Getting the German Article Outline translated to englisch ..."))
   #     de_outline_in_en = get_section_headlines(de_wiki_page.extract)
   #     log_area.text(_(f"Getting the French Article Outline translated to englisch ..."))
   #     fr_outline_in_en = get_section_headlines(fr_wiki_page.extract)
   #     outlines_in_en = [en_outline, de_outline_in_en, fr_outline_in_en]
   #     log_area.text(_(f"Merging Outlines to a new one ..."))
   #     new_wiki_outline = get_new_wiki_outline(en_outline, outlines_in_en[1:])
   #
   #     parsed_new_outline = mwparserfromhell.parse(new_wiki_outline)
   #     new_section_headlines = parsed_new_outline.filter_headings()
   #     sections_headlines = ''
   #     section_counter = 0
   #     for section in new_section_headlines:
   #         if section.level == 1:
   #             continue
   #         elif section.level == 2:
   #             if sections_headlines != '':
   #                 sections_headlines = section.title.strip()
   #             else:
   #                 if section_counter == read_to_section:
   #                     break
   #                 else:
   #                     sections_headlines = section.title.strip()
   #             section_counter += 1
   #         else:
   #             if sections_headlines != '':
   #                 sections_headlines += '\n' + section.title.strip()

   #     print(sections_headlines)
   #     snowflake_helper = SnowflakeHelper()

   #    needed_sections = snowflake_helper.determine_needed_sections(sections_headlines, en_outline, en_search_term)
   #     print("The needed sections of EN are: ", needed_sections)
        # Now extract the content for these sections, check if is komma separated
   #     needed_sections = needed_sections.split(',')
   #     needed_section_content = ''
   #     for needed_section in needed_sections:
   #         needed_section_content += get_needed_section_content(needed_section, en_outline, en_wiki_page.extract)

   #     print("The content of the needed sections is: ", needed_section_content)
   #     new_section = snowflake_helper.write_the_new_wikipedia_section(needed_section_content, sections_headlines,
   #                                                                    en_search_term)

   #    return None


def parse_outline_to_dict(outline_str):
    lines = outline_str.strip().split('\n')
    outline_dict = {}
    current_section = None
    current_subsections = []

    for line in lines:
        if line.startswith("## "):  # Level 2 heading
            if current_section:
                outline_dict[current_section] = current_subsections
            current_section = line[3:].strip()
            current_subsections = []
        elif line.startswith("### "):  # Level 3 heading
            current_subsections.append(line[4:].strip())

    if current_section:  # Add the last section
        outline_dict[current_section] = current_subsections

    return outline_dict

def get_section_index(section_name, outline_dict):
    section_titles = list(outline_dict.keys())
    if section_name in section_titles:
        return section_titles.index(section_name)
    return None

def get_section_content_by_index(wiki_extract, level, index):
    parsed = mwparserfromhell.parse(wiki_extract)
    sections = parsed.get_sections(levels=[level])
    if len(sections) > index:
        return sections[index].strip_code()
    return None

def get_needed_section_content(section_name, outline_str, wiki_extract):
    outline_dict = parse_outline_to_dict(outline_str)
    index = get_section_index(section_name, outline_dict)
    if index is not None:
        # Assume level 2 for simplicity; adjust as needed for your use case
        return get_section_content_by_index(wiki_extract, level=2, index=index)
    return None


@cache_with_disk()
def get_new_wiki_outline(en_outline, outlines, en_search_term):

    for outline in outlines:
        en_outline = improve_outline(en_outline, outline)

    new_outline = polish_outline(en_outline, en_search_term)
    return new_outline

def get_sections(extract, read_to_section, target_language, image_html=None):
    wikicode = mwparserfromhell.parse(extract)
    print(f"Section to read: {read_to_section}")
    print(len(wikicode.nodes))
    if read_to_section == 0:
        read_to_section = len(wikicode.nodes)
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


@cache_with_disk()
def translate(text, target_language, new_line=True, is_search_term=False):
    snowflake_helper = SnowflakeHelper()

    #if is_search_term:
    #    return snowflake_helper.translate_search_term_with_cortex(text, target_language)

    # TODO Dirty hack instead of chunking the text. Depending that wiki text is well formatted ;-)
    text_parts = text.split("\n")
    translated_text = ""
    for index, text_part in enumerate(text_parts):
        if len(text_part.strip()) > 0:
            translated_text += snowflake_helper.translate(text_part, target_language, is_search_term)
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
def get_translation(text, target_language, is_search_term=False):
    snowflake_helper = SnowflakeHelper()
    return snowflake_helper.translate(text, target_language, is_search_term)


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
