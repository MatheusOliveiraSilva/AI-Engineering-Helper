import os

from pinecone import Pinecone
from pinecone_text.sparse import BM25Encoder
from langchain_core.documents import Document
from vector_database.pinecone_utils import PineconeUtils
from preprocessment.embedding.embedding_config import EmbeddingConfig
from langchain_community.retrievers import PineconeHybridSearchRetriever
from pathlib import Path
from typing import List

class HybridSearchRetriever:
    def __init__(self,
                 index_name: str,
                 embedding_model_name: str,
                 embedding_provider: str,
                 top_k: int = 10
                 ) -> None:

        self.index = PineconeUtils(
            index_name=index_name,
            metric="dotproduct",
            embedding_model_name=embedding_model_name,
            embedding_provider=embedding_provider
        ).index

        self.sparse_encoder = self.get_sparse_encoder(index_name)

        self.embeddings = EmbeddingConfig(
            embedding_model=embedding_model_name,
            provider=embedding_provider
        ).get_embedding_model()

        # Passa o encoder corretamente como "sparse_encoder"
        self.retriever = PineconeHybridSearchRetriever(
            index=self.index,
            sparse_encoder=self.sparse_encoder,
            embeddings=self.embeddings,
            text_key="text",
            top_k=top_k
        )

    def get_sparse_encoder(self, index_name):
        # get this file absolute path
        current_dir = Path(__file__).resolve().parent
        sparse_encoder_weights = current_dir / "bm25_values.json"

        return BM25Encoder().load(sparse_encoder_weights) if sparse_encoder_weights.exists() \
                                                      else self.create_sparse_encoder_tdif(index_name)

    @staticmethod
    def create_sparse_encoder_tdif(index_name):
        pc = Pinecone(os.getenv("PINECONE_API_KEY"))
        index = pc.Index(index_name)

        # put all document ids in a list
        ids = []
        for id_list in index.list():
            ids.extend(id_list)

        # define a chunker function because we can load all vectors at once, we receive a HTTP error message
        def chunker(seq, size):
            return (seq[i:i + size] for i in range(0, len(seq), size))

        # We getting 100 documents per request
        chunk_size = 100
        all_vectors = {}

        for chunk in chunker(ids, chunk_size):
            result = index.fetch(ids=chunk)
            all_vectors.update(result.get("vectors", {}))

        # the corpus is basically the text of the documents, so:
        corpus = [v["metadata"]["text"] for v in all_vectors.values() if "metadata" in v and "text" in v["metadata"]]

        # We initialize a BM25 encoder with default td-if values and fit in our corpus:
        bm25_encoder = BM25Encoder().default()
        bm25_encoder.fit(corpus)

        # and finally save it to a file, so we can re-use in other retriever loadings:
        bm25_encoder.dump("bm25_values.json")

        encoder = BM25Encoder().load("bm25_values.json")

        return encoder

    def retrieve(self, query: str) -> List[Document]:
        """
        This function retrieves the top k documents from the database.
        """
        return self.retriever.invoke(query)

if __name__ == "__main__":
    retriever = HybridSearchRetriever(
        index_name="ca-contextualemb-dotp-3large",
        embedding_model_name="text-embedding-3-large",
        embedding_provider="openai"
    ).retriever

    documents = retriever.invoke("How HyDE works?")
    print(documents)
