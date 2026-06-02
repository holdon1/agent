from abc import ABC, abstractmethod

class BaseEmbedder(ABC):

    @abstractmethod
    def embed_documents(self, documents):
        pass

    @abstractmethod
    def embed_query(self, query):
        pass