import numpy as np


class MemoryVectorStore:

    def __init__(self):

        # 存储所有Document
        self.documents = []

    def add_documents(
        self,
        documents
    ):

        self.documents.extend(
            documents
        )

    def cosine_similarity(
        self,
        vec1,
        vec2
    ):

        vec1 = np.array(vec1)

        vec2 = np.array(vec2)

        numerator = np.dot(
            vec1,
            vec2
        )

        denominator = (
            np.linalg.norm(vec1)
            * np.linalg.norm(vec2)
        )

        return numerator / denominator

    def similarity_search(
        self,
        query_embedding,
        top_k=3
    ):

        scores = []

        for doc in self.documents:

            similarity = (
                self.cosine_similarity(
                    query_embedding,
                    doc.embedding
                )
            )

            scores.append(
                (doc, similarity)
            )

        # 按相似度排序
        scores.sort(
            key=lambda x: x[1],
            reverse=True
        )

        return scores[:top_k]