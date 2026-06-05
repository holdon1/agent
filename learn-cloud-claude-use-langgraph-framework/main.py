from pathlib import Path


from langgraph.checkpoint.memory import InMemorySaver

from s01_agent_loop import AgentState
from s05_todo_write import todo_write
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
)

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from langgraph.graph import StateGraph, END,START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode,tools_condition
from dotenv import load_dotenv
from langgraph.types import Command
from s03_permission_gate import permission_gate,route_after_chatbot
from s05_todo_write import todo_write

load_dotenv()

import subprocess
import os


# =========================
# State
# =========================



# =========================
# Tool
# =========================
from s02_tool_use import tools

# =========================
# Model
# =========================
llm = ChatOpenAI(
    model="glm-4-flash",
    api_key=os.getenv("ZHIPU_API_KEY"),
    base_url=os.getenv("ZHIPU_BASE_URL"),
    temperature=0.5
)
llm_with_tools = llm.bind_tools(tools)

# LLM节点
def chatbot(state: AgentState):
    """
    LLM 节点：根据消息和任务状态调用 llm_with_tools
    """
    response = llm_with_tools.invoke(state["messages"])

    return {
        "messages": [response],
    }

# =========================
# 构造器
# =========================
builder = StateGraph(AgentState)

# =========================
# 注册节点
# =========================
builder.add_node("chatbot", chatbot)
builder.add_node("tools",ToolNode(tools))
builder.add_node("permission",permission_gate)
# =========================
# 注册边
# =========================
# 开始边
builder.add_edge(START,"chatbot")
# chatbot到条件边（结束or使用工具）
builder.add_conditional_edges("chatbot",route_after_chatbot,
                              {'permission':'permission',
                                         END:END})
builder.add_edge("permission","tools")
# 工具调用到chatbot边
builder.add_edge("tools","chatbot")
# 记忆
memory = InMemorySaver()
# 图
graph = builder.compile(checkpointer=memory)

if __name__ == '__main__':
    user_input = "Refactor s05_todo_write/example/hello.py: add type hints, docstrings, and a main guard（先列 3 步再执行）"
    SYSTEM =  """
        你是一个终端Agent。
        
        在执行任何工具前，请遵循以下规则：
        
        1. 先调用 run_todo_write工具 生成执行计划
        2. 再调用具体工具执行任务
        3. 禁止直接回答
        4. 必须使用工具执行所有操作
        """

    config = {"configurable": {"thread_id": "1"}}
    graph.invoke(
        {
            "messages": [
                SystemMessage(content=SYSTEM),
                HumanMessage(content=user_input)
            ]
        },
        config=config
    )
    # 检查中断
    snapshot = graph.get_state(config)
    if snapshot.tasks:
        interrupt_value = snapshot.tasks[0].interrupts[0].value
        print(interrupt_value)
        # 用户审批
        ans = input("Approve? (y/n): ")
        # 回复中断-如果用户同意
        result = graph.invoke(
            Command(
                resume=(ans.lower() == "y")
            ),
            config=config
        )
    else:
        print("⚠️ 没有生成中断任务")

    # 最终回复
    final_state = graph.get_state(config)

    messages = final_state.values["messages"] # 消息列表

    last_ai = None

    for msg in reversed(messages): # 最后一条大模型回复
        if msg.type == "ai":
            last_ai = msg
            break

    if last_ai:                 # 打印
        print("\n🤖 FINAL ANSWER")
        print(last_ai.content)




