from pathlib import Path
from typing import TypedDict, Annotated

from langgraph.checkpoint.memory import InMemorySaver

from s01_agent_loop import AgentState
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


load_dotenv()

import subprocess
import os


# =========================
# State
# =========================



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
WORKDIR = Path.cwd()
def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path
@tool
def run_read(path, limit=None):
    """
    run read
    :param path:
    :param limit:
    :return:
    """
    lines = safe_path(path).read_text().splitlines()
    if limit:
        lines = lines[:limit]
    return "\n".join(lines)
@tool
def run_write(path, content):
    """
    run write
    :param path:
    :param content:
    :return:
    """
    safe_path(path).write_text(content)
    return f"Wrote {len(content)} bytes to {path}"
@tool
def run_edit(path, old_text, new_text):
    """
    run edit
    :param path:
    :param old_text:
    :param new_text:
    :return:
    """
    text = safe_path(path).read_text()
    if old_text not in text:
        return "Error: text not found"
    safe_path(path).write_text(text.replace(old_text, new_text, 1))
    return f"Edited {path}"
@tool
def run_glob(pattern):
    """
    run glob
    :param pattern:
    :return:
    """
    import glob as g
    return "\n".join(g.glob(pattern, root_dir=WORKDIR))
tools = [bash, run_read, run_write, run_edit, run_glob]
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
builder.add_node("permission",permission_gate)
# =========================
# 注册边
# =========================
# 开始边
builder.add_edge(START,"chatbot")
# chatbot到条件边（结束or使用工具）
builder.add_conditional_edges("chatbot",route_after_chatbot,
                              {'permission':'permission',END:END})

builder.add_edge("permission","tools")
# 工具调用到chatbot边
builder.add_edge("tools","chatbot")
# 记忆
memory = InMemorySaver()
# 图
graph = builder.compile(checkpointer=memory)

if __name__ == '__main__':
    user_input = "删除当前目录中的test.txt文件"
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
    interrupt_value = (
        snapshot.tasks[0]
        .interrupts[0]
        .value
    )
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
    # 最终回复
    final_state = graph.get_state(config)

    messages = final_state.values["messages"]

    last_ai = None

    for msg in reversed(messages):
        if msg.type == "ai":
            last_ai = msg
            break

    if last_ai:
        print("\n🤖 FINAL ANSWER")
        print(last_ai.content)




