from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
import bs4
from langchain_core.runnables import RunnableLambda
from langchain.chains import create_history_aware_retriever
from langchain_core.prompts import MessagesPlaceholder
import langchainhub as hub
load_dotenv()

llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash')
print(llm)
# 数据加载
loader = WebBaseLoader(
    web_paths=("https://lilianweng.github.io/posts/2023-06-23-agent/",),
    bs_kwargs=dict(
        parse_only=bs4.SoupStrainer(
            class_=("post-content", "post-title", "post-header")
        )
    ),
)
docs = loader.load()

# 数据分割
text_split = RecursiveCharacterTextSplitter(chunk_size=500,chunk_overlap=200,add_start_index=True)
all_splits = text_split.split_documents(docs)

# 数据存储（向量数据库）
embedding_model = HuggingFaceEmbeddings(model_name="BAAI/bge-small-zh-v1.5") # 嵌入模型

vector_store = Chroma.from_documents(documents=all_splits,embedding=embedding_model) # 向量数据库

# 数据检索（检索器）
retriever = vector_store.as_retriever(search_type="similarity",search_kwargs={"k":6})

# 整合（成一条链）
# 提示词
prompt = hub.pull("rlm/rag-prompt")
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)
# RAG
# 大模型
# 解析器
chain =  ({"context":retriever | RunnableLambda(format_docs),"question":RunnablePassthrough()}
         | prompt
         | llm
         | StrOutputParser())

# 流式输出
for chunk in chain.stream("What is Task Decomposition?"):
    print(chunk, end="", flush=True)