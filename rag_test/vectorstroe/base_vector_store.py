from abc import ABC, abstractmethod


class BaseVectorStore(ABC):

    @abstractmethod
    def add_documents(
        self,
        documents
    ):
        pass

    @abstractmethod
    def similarity_search(
        self,
        query_embedding,
        top_k=3
    ):
        pass