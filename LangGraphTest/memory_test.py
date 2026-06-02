import os

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI


from langgraph.checkpoint.memory import InMemorySaver
from dotenv import load_dotenv
load_dotenv()
memory = InMemorySaver()

