from typing import TypedDict, Annotated

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



load_dotenv()

import subprocess
import os


# =========================
# State
# =========================

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    pend_tool: dict|None
    todos: list[dict]
    todo_skip_count: int

# =========================
# Tool
# =========================
@tool
def bash(command: str) -> str:
    """Run a shell command."""

    dangerous = ["rm -rf /", "sudo", "shutdown"]

    if any(d in command for d in dangerous):
        return "Dangerous command blocked"

    try:
        r = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=os.getcwd(),
        )

        out = (r.stdout + r.stderr).strip()

        return out[:50000] if out else "(no output)"

    except Exception as e:
        return str(e)
tools = [bash]
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

    response = llm_with_tools.invoke(state["messages"])
    print("\n===== tool_calls =====")
    print(response.tool_calls)

    return {"messages": [response]}
# 条件边tool_condition


# =========================
# 构造器
# =========================
builder = StateGraph(AgentState)

# =========================
# 注册节点
# =========================
builder.add_node("chatbot", chatbot)
builder.add_node("tools",ToolNode(tools))
# =========================
# 注册边
# =========================
# 开始边
builder.add_edge(START,"chatbot")
# chatbot到条件边（结束or使用工具）
builder.add_conditional_edges("chatbot",tools_condition,)
# 工具调用到chatbot边
builder.add_edge("tools","chatbot")

graph = builder.compile()

if __name__ == '__main__':
    SYSTEM = """
    你是一个终端Agent。

    对于以下任务：

    - 文件查询
    - 目录查询
    - 系统信息查询
    - Shell命令执行

    必须调用bash工具。

    禁止直接回答。
    禁止输出命令。
    必须执行工具。
    """
    events = graph.stream(
        {
            "messages": [
                SystemMessage(content=SYSTEM),
                HumanMessage(content="当前目录有几个文件？")
            ]
        },
        stream_mode="values"
    )

    for event in events:
        messages = event.get("messages", [])
        if messages:
            last = messages[-1]

            # 只打印最终 AI 回复
            if last.type == "ai" and not last.tool_calls:
                print("\n🤖 FINAL ANSWER:")
                print(last.content)




