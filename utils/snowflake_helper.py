import os
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

    def translate(self, text, target_language):
        languages = {'de': 'German', 'en': 'English', 'fr': 'French', 'es': 'Spanish', 'it': 'Italian'}
        target_language = languages.get(target_language, 'English')

        prompt = f"""       
        You are a text and word translator. Your task is to translate text and single word from one language to another. 
        DO NOT add explanations. Answer ONLY with the translated text or word.
        If the text is one word return the translated word ONLY.
        If no translation is needed answer with the original text.
        If the text is a Noun or name answer with the original text.
                
        Now Translate the following text or word to {target_language}.
        ------------------------
        
        """

        # Artic Model can not translate very well, it is hallucianting, So fallback to Mistral
        response = self.session.sql(self.arctic_statement, params=(prompt, text))
        return response.first()[0]

    def summarize(self, text):
        prompt = f"""       
                You are a summarizer. Your task is to summarize the given text.
                This is a piece out of a larger wikipedia article. Summarize the text in 1-2 Sentences.
                If needed add up to three bullet points with the most important information.
                ------------------------
                """

        # Artic Model can not translate very well, it is hallucianting, So fallback to Mistral
        response = self.session.sql(self.arctic_statement, params=(prompt, text))
        return response.first()[0]
