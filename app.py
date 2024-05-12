import streamlit as st
from streamlit_extras.buy_me_a_coffee import button as coffee_button

import utils.wiki_utils as wiki_utils
from utils.app_utils import wiki_search, get_sections, get_article_image, get_translation, get_summary, get_strong_summary
from utils.localization import load_translations, set_language, _


def get_merged_knowledge(query, target_language):
    with st.spinner(_("Getting the German Wikipedia articles ...")):
        translated_query = get_translation(query, 'de')
        print("Searching German Wikipedia for ", translated_query)
        german_wiki_page = wiki_search(query, target_language='de')
    st.success(_("German Wikipedia articles retrieved."))
    with st.spinner(_("Getting the French Wikipedia articles ...")):
        print("Searching French Wikipedia for ", query)
        french_wiki_page = wiki_search(query, target_language='fr')
        st.success(_("French Wikipedia articles retrieved."))
    with st.spinner(_("Getting the Spanish Wikipedia articles ...")):
        print("Searching Spanish Wikipedia for ", query)
        spanish_wiki_page = wiki_search(query, target_language='es')
    st.success(_("Spanish Wikipedia articles retrieved."))
    with st.spinner(_("Getting the Italian Wikipedia articles ...")):
        print("Searching Italian Wikipedia for ", query)
        italian_wiki_page = wiki_search(query, target_language='it')
    st.success(_("Italian Wikipedia articles retrieved."))
    with st.spinner(_("Getting the English Wikipedia articles ...")):
        print("Searching English Wikipedia for ", query)
        english_wiki_page = wiki_search(query, target_language='en')
    st.success(_("English Wikipedia articles retrieved."))


translations = load_translations('locales')

if not 'target_language' in st.session_state:
    print("Setting default language to English")
    set_language('en')
else:
    print("Setting language to ", st.session_state['target_language'])
    set_language(st.session_state['target_language'])


def reset_section_position():
    print("Resetting section position")
    st.session_state['wiki_page'] = None
    st.session_state['read_to_section'] = 1


# Initialisierung der Streamlit App
st.set_page_config(page_title="Full Wiki Project", layout="wide")

st.markdown("""
<style>
.title {
    display: flex;
    align-items: center; 
    height: 200px;
}
div[data-testid="column"]:nth-of-type(2)
        {   
            display: flex;
            align-items: end;            
        }
div[data-testid="column"]:nth-of-type(3)
{
    display: flex;
    justify-content: flex-end;
    color: #f0f0f0;
}
div .stButton {
    min-width: 120px;
    }
div .stCheckbox {
    min-width: 240px;
    }
</style>
""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 3])
with col1:
    st.image("https://dannygerst.b-cdn.net/images/wikiglobe.png", width=200)
with col2:
    st.markdown('<div class="title"><h1>Full Wiki</h1></div>', unsafe_allow_html=True)
st.write(_("Full Wiki delivers the complete Wikipedia experience in your language of choice."))

# Sidebar nur für Informationen
with st.sidebar:
    st.header('Full Wiki')
    st.write(_("Full Wiki delivers the complete Wikipedia experience in your language of choice."))
    st.write("❶ ", _("Select your language"))
    st.write("❷ ", _("Enter a search term"))
    st.write("❸ ", _("Hit Search"))
    st.write(
             _("The most comprehensive English Wikipedia article will be retrieved and translated for you."))
    st.divider()
    st.write(
        _("Vou wish to harness the combined knowledge of all major languages?"))
    st.write("✅ ", _("Check the 'Merge Knowledge' box."))
    st.write(_("This process may take some time, but you will be rewarded with a comprehensive article that integrates "
             "knowledge from all major Wikipedia instances on the topic."))
    st.divider()
    st.text(_("Created by:"))
    st.write("Danny Gerst")
    st.write("[LinkedIn](https://www.linkedin.com/in/dannygerst/)")
    st.write("[Twitter](https://twitter.com/gerstdanny/)")
    st.write("[Website](https://www.dannygerst.de/)")
    coffee_button(username="dannygerst", floating=False)


# Hauptbereich für Suchfunktionen und Ergebnisse
with st.container():
    col1, col2 = st.columns([3, 1])
    with col1:
        old_language = st.session_state.get('target_language')
        languages = [['English', 'en'], ['Deutsch', 'de'], ['Français', 'fr'], ['Español', 'es'], ['Italiano', 'it']]
        labels = [language[0] for language in languages]
        codes = [language[1] for language in languages]
        if 'target_language' in st.session_state:
            selected_language = st.session_state['target_language']
            index = codes.index(selected_language)
        else:
            index = 0

        target_language = st.selectbox(key="target_language", index=index,
            label=_("Target Language"), options=codes, on_change=reset_section_position,
                                       format_func=lambda code: labels[codes.index(code)])

    with col2:
        merge_knowledge = st.checkbox(_("Merge Knowledge"))

    with st.form(key='my_form', border=False):
        col1, col2 = st.columns([3, 1])
        with col1:
            query = st.text_input(_("Search Term"), key="query", placeholder=_("Enter a search term..."))
        with col2:
            st_button = st.form_submit_button(_("Search"))

if merge_knowledge:
    st.write("⚠️", _("Merge Knowledge is activated. Downloading multiple articles and merging them. Will take some "
                     "time... (3-5 minutes)"), "⚠️")

if query and st_button:
    if 'target_language' in st.session_state and st.session_state['target_language'] != 'en':
        st.session_state['original_query'] = query
        query = get_translation(query, 'en')
        st.session_state['trans_query'] = query

    if merge_knowledge:
        wiki_page = get_merged_knowledge(query, target_language)
    else:
        with st.spinner(_("Getting Wikipedia article ...")):
            print("Searching Wikipedia for ", query)
            wiki_page = wiki_search(query)

    st.session_state['wiki_page'] = wiki_page
    st.session_state['read_to_section'] = 1
elif 'wiki_page' in st.session_state:
    wiki_page = st.session_state['wiki_page']
else:
    # result = None
    wiki_page = None

# Suchen und Ergebnis anzeigen
if 'next_section_btn' in st.session_state and st.session_state.next_section_btn:
    st.session_state['read_to_section'] += 1
    print("Next Section ", st.session_state['read_to_section'])

if wiki_page and isinstance(wiki_page, wiki_utils.WikipediaPage):
    if 'original_query' in st.session_state:
        original_query = st.session_state['original_query']
        trans_query = st.session_state['trans_query']
        st.header(f"{original_query} => {trans_query}")
    else:
        st.header(query)
    st.write(f"[Wikipedia]({wiki_page.url})")
    extract = wiki_page.extract
    infobox = wiki_page.infobox

    image_filename = None
    if infobox:
        image_filename = infobox.get('image')
    if not image_filename:
        image_filename = wiki_page.image_name
    image_html = get_article_image(image_filename)

    if 'summary_btn' in st.session_state and st.session_state.summary_btn:
        with st.spinner(_("Summarizing Wikipedia article ... (Takes 1-2 minutes)")):
            print("Summarizing Wikipedia article ...")
            summary = get_summary(extract=extract, target_language=target_language, image_html=image_html)
            st.session_state['summary'] = summary
        st.write(_("Summary"))
        st.markdown(summary, unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col3:
            strong_summary_btn = st.button(_("Strong Summary"), key="strong_summary_btn")
            st.write(f'<p style="font-size:0.8rem; padding-left: 5px; margin-top: -8px; color: lightblue">'
                     f'{_("Takes a while until finished")}</p>', unsafe_allow_html=True)
    elif 'strong_summary_btn' in st.session_state and st.session_state.strong_summary_btn:
        with st.spinner(_("Strong Summarizing Wikipedia article ... (up to 1 minute)")):
            print("Strong Summarizing Wikipedia article ...")
            if 'summary' in st.session_state and st.session_state['summary']:
                summary = st.session_state['summary']
                st.session_state['summary'] = None
            else:
                summary = get_summary(extract=extract, target_language=target_language, image_html=image_html)

            strong_summary = get_strong_summary(summary=summary, target_language=target_language, image_html=image_html)
        st.write(_("Strong Summary"))
        st.markdown(strong_summary, unsafe_allow_html=True)
    else:
        with st.spinner(_("Translating Wikipedia article ...")):
            print("Retrieving Section ", st.session_state['read_to_section'])
            sections = get_sections(extract, st.session_state['read_to_section'], target_language, image_html=image_html)

        st.markdown(sections, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            # TODO only show if section to read is smaller that the number of sections
            next_section_btn = st.button(_("Next Section"), key="next_section_btn")
        with col3:
            summary_btn = st.button(_("Summary"), key="summary_btn")
            st.write(f'<p style="font-size:0.8rem; padding-left: 5px; margin-top: -8px; color: lightblue">'
                     f'{_("Takes a while until finished")}</p>', unsafe_allow_html=True)
else:
    st.header(_("Please enter a search query to get started."))

