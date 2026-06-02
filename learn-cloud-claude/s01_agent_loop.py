from typing import TypedDict, Annotated

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
)

from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
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


tools = [bash]


# =========================
# Model
# =========================

llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash')

llm_with_tools = llm.bind_tools(tools)


# =========================
# Agent Node
# =========================

SYSTEM = f"""
You are a coding agent at {os.getcwd()}.
Use bash to solve tasks.
Act, don't explain.
"""


def call_model(state: AgentState):

    response = llm_with_tools.invoke([
        SystemMessage(content=SYSTEM),
        *state["messages"]
    ])

    return {
        "messages": [response]
    }


# =========================
# Continue Logic
# =========================

def should_continue(state: AgentState):

    last_message = state["messages"][-1]

    # 是否调用tool
    if last_message.tool_calls:
        return "tools"

    return END


# =========================
# Graph
# =========================

builder = StateGraph(AgentState)

builder.add_node("agent", call_model)

builder.add_node(
    "tools",
    ToolNode(tools)
)

builder.set_entry_point("agent")

builder.add_conditional_edges(
    "agent",
    should_continue,
)

builder.add_edge("tools", "agent")

graph = builder.compile()


# =========================
# Run
# =========================

if __name__ == "__main__":

    while True:

        query = input(">> ")

        if query in ["q", "exit"]:
            break

        result = graph.invoke({
            "messages": [
                HumanMessage(content=query)
            ]
        })

        print("\n=== FINAL ANSWER ===\n")

        print(result["messages"][-1].content)