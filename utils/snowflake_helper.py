import os
import re
from dotenv import load_dotenv

from snowflake.snowpark import Session


class SnowflakeHelper:

    def __init__(self):
        load_dotenv('.env')
        connection_parameters = {
            "account": os.environ["SNOWFLAKE_ACCOUNT_NAME"],
            "user": os.environ["SNOWFLAKE_USER"],
            "password": os.environ["SNOWFLAKE_PASSWORD"],
            "role": "ACCOUNTADMIN",
            "database": os.environ["SNOWFLAKE_DATABASE"],
            "warehouse": os.environ["SNOWFLAKE_WAREHOUSE"],
            "schema": os.environ["SNOWFLAKE_SCHEMA"],
        }
        self.session = Session.builder.configs(connection_parameters).create()
        #self.arctic_statement = "select snowflake.cortex.complete('snowflake-arctic', concat('[INST]',?,?,'[/INST]'))"
        self.mistral_statement = "select snowflake.cortex.complete('mixtral-8x7b', concat(?,?))"
        self.arctic_statement = "select snowflake.cortex.complete('snowflake-arctic', concat(?,?))"
        self.translation_statement = "select snowflake.cortex.translate(?,?,?)"

    def __del__(self):
        self.session.close()

    def translate_search_term_with_cortex(self, search_term, target_language):
        # Unfortunately translation is not working good for single words with arctic
        response = self.session.sql(self.translation_statement, params=(search_term, 'en', target_language))
        return response.first()[0]

    def translate(self, text, target_language, is_search_term=False):
        languages = {'de': 'German', 'en': 'English', 'fr': 'French', 'es': 'Spanish', 'it': 'Italian'}
        target_language = languages.get(target_language, 'English')

        if is_search_term:
            translation_prompt = f"""
            You are a search term translator. Your task is to translate the search term to {target_language}.
                            
            It is important, that your output is ONLY the translated search term.
                            
            Now translate the search term {text} to {target_language}.
            Think step by step.
            Verify that the translation is 100% correct. Before outputting.
            
            Make the output a translated search term without naming the original search term nor a language.
            Do not provide any further information.
            Make the output the translated search term only.
            """
        else:
            translation_prompt = f"""       
            You are a an expert translator. Your task is to translate text from one language to another. 
            
            DO NOT add explanations. 
            Answer ONLY with the translated text without naming the original search term nor a language.                            
                        
            Now Translate the following text to {target_language}:
                           
            {text}    
            """

        response = self.session.sql(self.arctic_statement, params=(translation_prompt, ''))

        if is_search_term:
            search_term_draft = response.first()[0]
            match = re.search(r'"([^"]*)"', search_term_draft)
            if match:
                return match.group(1)

        return response.first()[0]

    def summarize(self, text):
        prompt = f"""       
                You are a summarizer. Your task is to summarize the given text.
                This is a piece out of a larger wikipedia article. Summarize the text in 1-2 Sentences.
                If needed add up to three bullet points with the most important information.
                
                """

        response = self.session.sql(self.arctic_statement, params=(prompt, text))
        return response.first()[0]

    def improve_article_outline(self, english_outline, foreign_outline):

        prompt = f"""
                You need to improve an outline for a Wikipedia page, based on the outline from other wikipedia page.
                The first outline came from the english wikipedia page.
                The second outline came from the translation of the same topic in different languages.
                
                Your task is to improve the outline of the english wikipedia page.
                See if you can add more sections or subsections to the outline from the translation.
                Or maybe you need to rearrange or rename some sections.
                                 
                Write than an outline for a Wikipedia page.
                Here is the format of your writing:
                1. Use "#" Title" to indicate section title, "##" Title" to indicate subsection title, "###" Title" to indicate subsubsection title, and so on.
                2. Do not include other information.
                3. Do not include topic name itself in the outline.
        
                Make it step by step.                
                               
                outline from english wikipedia page:
                {english_outline}
                
                outline from translation:
                {foreign_outline}
                """

        response = self.session.sql(self.arctic_statement, params=(prompt, ''))
        return response.first()[0]

    def polish_outline(self, outline, wiki_query):
        prompt = f"""
                You need to polish an outline for a new Wikipedia page with the topic {wiki_query}.
                
                Your task is to polish the outline for a new Wikipage.
                Think step by step and consolidate or expand the outline.
                Maybe you need to rearrange or rename some sections.
                
                Write then the polished outline for a Wikipedia page.
                section title is equals to the topic name.
                
                Here is the format of your writing:
                1. Use "#" Title" to indicate section title, "##" Title" to indicate subsection title, "###" Title" to indicate subsubsection title, and so on.
                2. Do not include other information.
                3. Do not include topic name itself in the outline.

                Think step by step.                
                               
                current outline:
                {outline}

                polished outline:                
                """

        response = self.session.sql(self.arctic_statement, params=(prompt, ''))
        return response.first()[0]

    def combine_sections(self, master_section, compare_section):
        prompt = f"""
                        You will rewrite a master section with information from a compare section.
                        You need to extract new information from a compare section that do not exists in the master 
                        section.                        
                        The final result will be a section for a Wikipedia page. 
                        Do not show the new information separate but include it in to the final section as text.
                        So do not include more that the combined content of the master section and the information
                        missing from the compare section.
                        
                        If you do not find any useful information to enrich the master section in the compare section, 
                        return the master section as it is.
                        
                        The output should be well formatted and as extended as possible. Hold all information.
                        
                        Think step by step.                
                                       
                        Master section:
                        {master_section}

                        Compare Section:
                        {compare_section}    
                        
                        Final Section:            
                        """

        response = self.session.sql(self.arctic_statement, params=(prompt, ''))
        return response.first()[0]

    def combine_sections_2(self, combined_section):
        prompt = f"""
                You are an expert Wikipedia editor.
                Here you find a text that is a combination of multiple sources.
                
                Use all information and create on unified text.
                Make the text as long as possible. Use all information from the sources.
                That is VERY important to me!!
                
                Rewrite step by step.                
                               
                Knowlegde sources:
                {combined_section}
                
                Combined new Section:            
                """
        print(prompt)
        response = self.session.sql(self.arctic_statement, params=(prompt, ''))
        return response.first()[0]

    def rewrite_article_section(self, section, wiki_query):
        prompt = f"""
                    # MISSION
                    You are a Wikipedia editor and an excellent writer of Wikipedia articles.
                    You are a master of taking single information and rewriting it in a way that is easy to understand.
                    You LOVE to write LONG and EXTENDED articles.                    
                    
                    # METHODOLOGY
                    Use all information from the input and create a new abstract for a Wikipedia page.
                    The Topic is about {wiki_query}.
                    Make it as long as possible. Use all information from the input.
                    People should LOVE this article and your way to write it that LONG and EXTENDED. 
                    What a great article that would be.
                    
                    # INPUT
                    {section}
                    """

        response = self.session.sql(self.arctic_statement, params=(prompt, ''))
        return response.first()[0]

    def determine_needed_sections(self, master_outline, compare_outline, wiki_query):
        prompt = f"""
                        You are a Wikipedia editor. 
                        You are writing about {wiki_query}.
                        
                        You need to write another section about the topic. Your current section is:
                        {master_outline}
                        
                        You have access to a remote knowledge base. The knowledge base contains the following data 
                        accessible by the following key: 
                        {compare_outline}
                        
                        What data from what entries will you need to write the current section?
                        Output one key or a list of keys separated by a comma. The key must contain in the knowledge 
                        base.  
                        
                        See the four examples for reference:
                        key1
                        key2,key3
                        key4
                        key1,key2,key3,key4
                                               
                        """

        response = self.session.sql(self.arctic_statement, params=(prompt, ''))

        return response.first()[0]

    def write_the_new_wikipedia_section(self, master_content, current_section, wiki_query):
        prompt = f"""
                        You are a Wikipedia editor and an excellent writer of Wikipedia articles. 
                        You are writing about {wiki_query}.

                        You need to write another section about the topic. Your current section is:
                        {current_section}
                        
                        Use the following knowledge to write your current section:
                        {master_content}
                        
                        Now write this section.
                        """

        response = self.session.sql(self.arctic_statement, params=(prompt, ''))

        return response.first()[0]

    def extract_keyfacts(self, text, wiki_query):
        prompt = f"""
                    # MISSION
                    You are a Sparse Priming Representation (SPR) writer. 
                    An SPR is a particular kind of use of language for advanced NLP, NLU, and NLG tasks, 
                    particularly useful for the latest generation of Large Language Models (LLMs). 
                    You will be given information by the USER which you are to render as an SPR.

                    # THEORY
                    LLMs are a kind of deep neural network. 
                    They have been demonstrated to embed knowledge, abilities, and concepts, ranging from reasoning 
                    to planning, and even to theory of mind. These are called latent abilities and latent content, 
                    collectively referred to as latent space. The latent space of an LLM can be activated with the 
                    correct series of words as inputs, which will create a useful internal state of the neural network. 
                    This is not unlike how the right shorthand cues can prime a human mind to think in a certain way. 
                    Like human minds, LLMs are associative, meaning you only need to use the correct associations to 
                    "prime" another model to think in the same way.

                    # METHODOLOGY
                    Render the input as a distilled list of succinct statements, assertions, associations, concepts, 
                    analogies, and metaphors. The idea is to capture as much, conceptually, as possible but with as few 
                    words as possible. Write it in a way that makes sense to you, as the future audience will be 
                    another language model, not a human. Use complete sentences.
                    
                    # INPUT about {wiki_query}                    
                    {text}
                    """

        response = self.session.sql(self.arctic_statement, params=(prompt, ''))

        return response.first()[0]
