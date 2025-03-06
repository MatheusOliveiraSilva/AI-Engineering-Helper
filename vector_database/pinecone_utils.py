from uuid import uuid4
from pinecone import Pinecone, ServerlessSpec
from langchain_core.documents import Document
from langchain_pinecone import PineconeVectorStore
from preprocessment.embedding.embedding_config import EmbeddingConfig
from typing import List
import os

class PineconeUtils:
    def __init__(self,
                 index_name: str,
                 embedding_model_name: str,
                 embedding_provider: str,
                 metric: str
                 ):
        """
        This class is responsible for connecting to a Pinecone index and make operations on that.
        """
        self.index_name = index_name
        self.metric = metric
        self.pc_client = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
        self.embedding_config = EmbeddingConfig(embedding_model=embedding_model_name, provider=embedding_provider)
        self.embedding_model = self.embedding_config.get_embedding_model()

        if self.index_exists(self.index_name):
            print(f"Index {self.index_name} already exists, loaded.")
        else:
            print(f"Index {self.index_name} does not exist, creating...")
            self.create_index()

        self.index = self.pc_client.Index(index_name)
        self.vector_store = PineconeVectorStore(index=self.index, embedding=self.embedding_model)

    def insert_documents(self, documents: List[Document]) -> None:
        uuids = [str(uuid4()) for _ in range(len(documents))]

        self.vector_store.add_documents(documents=documents, ids=uuids)

    def create_index(self) -> None:
        self.pc_client.create_index(
            name=self.index_name,
            dimension=self.setup_dimension(self.embedding_config.embedding_model_name),
            metric=self.metric,
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        # Wait for the index to be created
        while not self.pc_client.describe_index(self.index_name).status["ready"]:
            time.sleep(1)

        print(f"Index {self.index_name} created.")

    def index_exists(self, index_name: str) -> bool:
        """
        This function checks if the index name exists in Pinecone.
        """
        existing_indexes = [index_info["name"] for index_info in self.pc_client.list_indexes()]
        return index_name in existing_indexes

    @staticmethod
    def setup_dimension(model_name: str) -> int:
        """
        This function sets up the model dimensions for the model.
        """

        models_vector_dimension = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-large": 3072
        }

        if model_name in models_vector_dimension:
            return models_vector_dimension[model_name]
        else:
            raise ValueError("This embedding model is not supported in this application.")

if __name__ == "__main__":
    pinecone_utils = PineconeUtils(
        # This index on test is the index used in this project, the name is a abreviation of:
        # 1. context aware chunked
        # 2. contextual embeddings documents
        # 3. dot product similarity
        # 4. embedded with text-embedding-3-large embedding model
        index_name="ca-contextualemb-dotp-3large",
        embedding_model_name="text-embedding-3-large",
        embedding_provider="azure",
        metric="dotproduct"
    )
    # Here is printed that already exists, passed test, check feeding_vector_db.py for more info on how this was created.
