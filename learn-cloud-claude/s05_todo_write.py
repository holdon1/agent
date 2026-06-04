from langchain_core.messages import HumanMessage,SystemMessage

from s01_agent_loop import AgentState,llm_with_tools
from s02_tool_use import run_todo_write

def todo_write(state: AgentState):
    last_msg = state["messages"][-1].content

    new_tasks = [
        {"content": f"理解任务: {last_msg}", "status": "pending"},
        {"content": "分析需求", "status": "pending"},
        {"content": "执行操作", "status": "pending"},
    ]

    todos = state.get("todos", []) + new_tasks
    todo_skip_count = state.get("todo_skip_count", 0)
    print("\n===== TODO WRITE =====")
    for t in todos:
        print("-", t["content"])

    return {
        "todos": todos,
        "todo_skip_count": int((todo_skip_count + 1) % 3),
    }

