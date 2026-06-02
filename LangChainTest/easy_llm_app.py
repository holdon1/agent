from pathlib import Path

from dotenv import load_dotenv
import os

from fastapi import FastAPI
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage,SystemMessage,AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langserve import add_routes

# 环境遍历配置
current_file_path = Path(__file__)
project_root_path = current_file_path.parent.parent
env_path = project_root_path / ".env"
load_dotenv(env_path)
print(os.getenv("LANGCHAIN_API_KEY"))
print(os.getenv("LANGCHAIN_TRACING_V2"))
print(os.getenv("GOOGLE_API_KEY"))

# 使用语言模型
model = ChatGoogleGenerativeAI(model='gemini-2.5-flash')
# 解析器
parser = StrOutputParser()
messages = [
    SystemMessage(content="Translate the following from English into Italian"),
    HumanMessage(content="hi")
]

# 提示词模板
system_template = "Translate the following into {language}:"
prompt_template = ChatPromptTemplate.from_messages(
    [
        ("system",system_template),
        ("user","{text}")
    ]
)
# 链
chain = prompt_template | model | parser

app = FastAPI(
    title="LangChain Server",
    version="1.0",
    description="A simple API server using LangChain's Runnable interfaces",
)

add_routes(
    app,
    runnable=chain,
    path="/chain"
)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app,host="localhost",port=8050)