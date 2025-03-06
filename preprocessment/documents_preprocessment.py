import os
import time
from tqdm import tqdm
from typing import List
from pathlib import Path
from dotenv import load_dotenv
from anthropic import RateLimitError
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from llm_config.llm_model_config import LLMModelConfig
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.messages import SystemMessage, HumanMessage

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(dotenv_path=ROOT_DIR / '.env')

class Preprocesser:
    def __init__(self,
                 preprocessing_technique: str = None
                 ) -> None:

        llm_config = LLMModelConfig('anthropic')
        self.llm = llm_config.get_llm_model(
            model_name="claude-3-7-sonnet-latest"
        )

        self.preprocessing_technique = preprocessing_technique

    def contextual_embedding(self, docs: List[Document]) -> List[Document]:
        """
        Function that apply contextual embedding preprocessment for each document in input list.
        """
        for doc in tqdm(docs, desc="Augmenting chunks using contextual embeddings strategy..."):
            source_doc_path = doc.metadata['source']
            loader = PyPDFLoader(source_doc_path)
            source_doc_pages = loader.load()

            full_source_document = ""
            for page in source_doc_pages:
                full_source_document += page.page_content + "\n"

            sys_msg = f"""
Considering the full document:
<document>
{full_source_document}
</document>
"""
            human_msg = f"""
Here is the chunk we want to situate within the whole document:
<chunk>
{doc.page_content}
</chunk>

Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk.
Answer only with the succinct context and nothing else.
"""
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=[{
                    "text": sys_msg,
                    "type": "text",

                    # Since we are sending multiple times the same global document, we can send it once with the
                    # flag to be cached, and in next times 5 minutes this tokens will have 90% discount to be
                    # used again. To learn more: https://www.anthropic.com/news/prompt-caching.
                    "cache_control": {"type": "ephemeral"}
                }]),
                HumanMessage(content=human_msg)
            ])

            # Try/except because of api limit, some chunks can be so big that raises the limit error.
            try:
                result = self.llm.invoke(prompt.messages)
            except RateLimitError:
                print("\nRate limit error. Waiting 60 sec before trying again...")
                time.sleep(60)
                try:
                    result = self.llm.invoke(prompt.messages)
                except RateLimitError as e:
                    print("Rate limit persists. Skipping this chunk. \n", e)
                    continue

            # Add the global context to the end of the document content.
            doc.page_content += "\n" + result.content

        return docs

    def preprocess_documents(self, docs: List[Document]) -> List[Document]:
        if self.preprocessing_technique == "contextual-embedding":
            return self.contextual_embedding(docs)
        return docs


if __name__ == "__main__":

    # You should have runned ./scripts/install.sh to have the documents in the right place and test this code.
    docs = [
        Document(
            metadata={'source': ROOT_DIR / 'documents/hyde.pdf'},
            page_content='Precise Zero-Shot Dense Retrieval without Relevance Labels\n\nLuyu Gao∗ † Xueguang Ma∗ ‡\n\nJimmy Lin‡\n\nJamie Callan†\n\n†Language Technologies Institute, Carnegie Mellon University ‡David R. Cheriton School of Computer Science, University of Waterloo {luyug, callan}@cs.cmu.edu, {x93ma, jimmylin}@uwaterloo.ca\n\nAbstract'
        )
    ]

    preprocessor = Preprocesser(preprocessing_technique="contextual-embedding")
    print(preprocessor.preprocess_documents(docs=docs))
