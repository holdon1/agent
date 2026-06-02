from rag_test.embeddings.beg_embedder import BGEEmbedder
from rag_test.loaders.txt_loader import TextDocumentLoader

from rag_test.splitters.character_splitter import CharacterSplitter
from rag_test.vectorstroe.memory_vector_store import MemoryVectorStore
txt_path = r"D:\Code\PycharmProjects\PythonProject\rag_test\knowledge.txt"
text_document_loader = TextDocumentLoader(txt_path)
text_document = text_document_loader.load()
character_splitter = CharacterSplitter()
embedding_model = BGEEmbedder()
embeddings = ""
memory_vector_store = MemoryVectorStore()
for doc in text_document:
    chunks = character_splitter.split(doc)
    print(f'chunks lens: {len(chunks)}')
    embeddings = embedding_model.embed_documents(chunks)
    print(f'embeddings lens: {len(embeddings)}')

print(embeddings)
memory_vector_store.add_documents(embeddings) # 添加向量化文档

query = "什么是FastApi"
query_embedding = embedding_model.embed_query(query)
scores = memory_vector_store.similarity_search(query_embedding)
print(scores)