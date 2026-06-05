from pathlib import Path
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
@tool
def run_todo_write(current_todos: list[dict], new_tasks: list[str] = []) -> list[dict]:
    """
    更新和显示任务列表
    - current_todos: 当前的任务列表
    - new_tasks: 新增的任务（默认为空）
    """
    # 复制一份，避免修改原引用
    todos = [t.copy() for t in current_todos]

    # 添加新任务
    for t in new_tasks:
        todos.append({"content": t, "status": "pending"})

    # 打印任务状态
    lines = ["\n## Current Tasks"]
    for t in todos:
        status = t.get("status", "pending")
        icon = {"pending": " ", "in_progress": "▸", "completed": "✓"}.get(status, " ")
        lines.append(f"  [{icon}] {t.get('content', '<no content>')}")
    print("\n".join(lines))

    # 返回更新后的任务列表给 AgentState 使用
    return todos

tools = [bash, run_read, run_write, run_edit, run_glob,run_todo_write]







