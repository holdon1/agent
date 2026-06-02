from typing import List

from sentence_transformers import (
    SentenceTransformer
)

from rag_test.loaders.base_document import Document


class BGEEmbedder:

    def __init__(
        self,
        model_name="BAAI/bge-small-en-v1.5"
    ):

        self.model = SentenceTransformer(
            model_name
        )

    def embed_documents(self, documents:List[Document]):

        texts = [
            doc.content
            for doc in documents
        ]

        embeddings = self.model.encode(texts)

        return embeddings

    def embed_query(self, query):

        embedding = self.model.encode(query)

        return embedding