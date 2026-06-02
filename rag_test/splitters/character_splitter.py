
from rag_test.loaders.txt_loader import TextDocumentLoader
from rag_test.loaders.base_document import Document
class CharacterSplitter:
    def __init__(self,chunk_size=20,chunk_overlap=5):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap


    def split(self, document:Document):
        chunks = []
        text = document.content
        start = 0
        step = self.chunk_size - self.chunk_overlap
        text_length = len(text)
        chunk_id = 0
        while start < text_length:
            end = min(start + self.chunk_size, text_length)
            chunk_text = text[start:end]
            chunks.append(
                Document(
                    content=chunk_text,
                    metadata={
                        **document.metadata,
                        "chunk_id": chunk_id
                    }
                )
            )
            start = start + step
            chunk_id += 1
        return chunks

