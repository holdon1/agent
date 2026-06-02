from pathlib import Path

from dotenv import load_dotenv
import os

from fastapi import FastAPI
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage,SystemMessage,AIMessage,trim_messages
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langserve import add_routes
from langchain_core.chat_history import BaseChatMessageHistory,InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
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
parser = StrOutputParser()
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
             "You are a helpful assistant. Answer all questions to the best of your ability in {language}.",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)
chain = prompt | model
# response = chain.invoke({"messages": [HumanMessage(content="hi! I'm bob")]})
# print(response.content)
# 临时数据库
store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    """
    获取存储的记忆，如果没有则新增到数据库
    看作记忆取货员
    :param session_id:
    :return:
    """
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

# 智能记忆外壳
with_message_history = RunnableWithMessageHistory(chain, get_session_history)
# response = chain.invoke(
#     {"messages": [HumanMessage(content="hi! I'm bob")], "language": "Spanish"}
# )

trimmer = trim_messages(
    max_tokens=65,
    strategy="last",
    token_counter=model,
    include_system=True,
    allow_partial=False,
    start_on="human",
)

messages = [
    SystemMessage(content="you're a good assistant"),
    HumanMessage(content="hi! I'm bob"),
    AIMessage(content="hi!"),
    HumanMessage(content="I like vanilla ice cream"),
    AIMessage(content="nice"),
    HumanMessage(content="whats 2 + 2"),
    AIMessage(content="4"),
    HumanMessage(content="thanks"),
    AIMessage(content="no problem!"),
    HumanMessage(content="having fun?"),
    AIMessage(content="yes!"),
]

trimmer.invoke(messages)