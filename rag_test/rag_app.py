from pathlib import Path

from openai import OpenAI
from sentence_transformers import SentenceTransformer
import numpy as np
from dotenv import load_dotenv
import os
current_file = Path(__file__) # 当前文件路径
project_root = current_file.parent.parent # 根目录
env_path = project_root / ".env" # env文件路径
load_dotenv(env_path) # 加载
print(os.getenv("LLM_BASE_URL"))
# 1.初始化 -嵌入模型，大模型客户端
client = OpenAI(base_url=os.getenv("LLM_BASE_URL"),api_key=os.getenv("LLM_API_KEY"))
embedding_model = SentenceTransformer("BAAI/bge-small-en-v1.5")
# 2.读取知识库
with open("knowledge.txt","r",encoding="utf-8") as f:
    documents = f.readlines()
# 3.分块
documents = [doc.strip() for doc in documents if doc.strip()]

# 4.向量化存储
doc_embeddings = embedding_model.encode(documents)
# 5.用户提问

# 6.根据相似度检索相关知识
def cosine_similarity(a, b):
    """
    计算两个向量之间的余弦值
    :param a:
    :param b:
    :return:
    """
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
def retrieve(query,top_k:int=2):
    """
    检索知识库，获取与query最相似的两个回答
    :param query:
    :param top_k:
    :return:
    """
    scores = []
    query_embedding = embedding_model.encode(query)
    # 遍历向量数据库，获取其分块以及索引
    for idx,doc_embedding in enumerate(doc_embeddings):

        # 分别计算每个向量与query向量的余弦相似度，并将分数，以及根据索引获取的文档原文快添加到分数数组
        score = cosine_similarity(query_embedding,doc_embedding)
        scores.append((score,documents[idx]))
    # 返回前top_k分数的分块
    scores.sort(reverse=True)
    return scores[:top_k]
# 7.获取知识构造好上下文，然后增强提示词
def rag_chat(query):

    retrieve_docs = retrieve(query)
    # 构造上下文
    context = "\n".join([doc for _,doc in retrieve_docs])

    prompt = f"""
    你是一个问答助手。

    已知知识：
    {context}

    用户问题：
    {query}

    请根据知识回答。
    """
    message = [
        {"role":"user",
         "content":prompt,}
    ]
    response = client.chat.completions.create(model=os.getenv("LLM_MODEL_ID"),messages=message)

    return response.choices[0].message.content
# 8.获取回答

if __name__ == '__main__':

    query = "什么是FastApi"

    answer = rag_chat(query)

    print("\n回答：")
    print(answer)