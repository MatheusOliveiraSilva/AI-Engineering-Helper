from preprocessment.chunking.content_aware_chunking import ContentAwareChunking
from vector_database.pinecone_utils import PineconeUtils
from langchain_community.document_loaders import DirectoryLoader
from preprocessment.documents_preprocessment import Preprocesser
from pathlib import Path

class Ingestion:
    def __init__(self,
                 index_name,
                 directory, embedding_model_name, metric,
                 preprocessing_technique: str = "None",
                 model_provider: str = 'openai',
                 glob: str = '*.pdf'):
        """
        This class is responsible for taking a path and parameters sending the documents on that path to a
        Pinecone index.
        """
        self.chunk_size = 512
        self.chunk_overlap = 50
        self.chunker = ContentAwareChunking(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        ).get_chunker()

        print("[Ingestion pipeline] Loading documents...")
        self.docs = self.load_documents(directory, glob)

        print("[Ingestion pipeline] Chunking documents...")
        self.chunked_docs = self.chunker.split_documents(self.docs)

        if preprocessing_technique != "None":
            print(f"[Ingestion pipeline] Preprocessing documents (with {preprocessing_technique} strategy)...")
            self.chunked_docs = self.preprocess_documents(self.chunked_docs, preprocessing_technique)

        print("[Ingestion pipeline] Sending documents into Pinecone...")
        self.pinecone_utils = PineconeUtils(
            index_name=index_name,
            metric=metric,
            embedding_model_name=embedding_model_name,
            embedding_provider=model_provider
        )

        self.pinecone_utils.insert_documents(self.chunked_docs)
        print("[Ingestion pipeline] Done!")

    @staticmethod
    def preprocess_documents(docs, preprocessing_technique):
        preprocessor = Preprocesser(preprocessing_technique)
        return preprocessor.preprocess_documents(docs)

    @staticmethod
    def load_documents(directory, glob):
        return DirectoryLoader(
            directory, glob=glob, show_progress=True
        ).load()

if __name__ == "__main__":
    ROOT_DIR = Path(__file__).parent.parent
    path = ROOT_DIR / 'documents'

    ingestion = Ingestion(
        index_name="ca-contextualemb-dotp-3large",
        metric='dotproduct',
        directory=path,
        embedding_model_name='text-embedding-3-large',
        preprocessing_technique='contextual-embedding'
    )
