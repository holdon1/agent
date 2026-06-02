import os
from typing import Annotated

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langgraph.types import interrupt
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from memory_test import memory
from dotenv import load_dotenv
from tools_test import tools, tool_node
from langchain_core.tools import tool
load_dotenv()

class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]


graph_builder = StateGraph(State)
# 语言模型
llm = ChatOpenAI(
    model="glm-4.7-flash",
    api_key=os.getenv("ZHIPU_API_KEY"),
    base_url=os.getenv("ZHIPU_BASE_URL"),
    temperature=0.5
)
llm_with_tools=llm.bind_tools(tools=tools)
# 节点一,调用大模型
def chatbot(state: State):
    message = llm_with_tools.invoke(state["messages"])
    assert len(message.tool_calls) <= 1
    return {"messages": [message]}

graph_builder.add_node("chatbot", chatbot)
# 节点二，工具使用
graph_builder.add_node("tools", ToolNode(tools=tools))

# 路由函数
def route_tools(
    state: State,
):
    """
    Use in the conditional_edge to route to the ToolNode if the last message
    has tool calls. Otherwise, route to the end.
    如果使用tools_condition，这个函数就不需要添加到条件边，
    """
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError(f"No messages found in input state to tool_edge: {state}")
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"
    return END

# 条件边(包含节点出口)
graph_builder.add_conditional_edges(
    # chatbot节点结束后，不沿着边执行下一个节点，而是先进行判断。判断条件是tools_condition
    "chatbot",
    tools_condition,
    # The following dictionary lets you tell the graph to interpret the condition's outputs as a specific node
    # It defaults to the identity function, but if you
    # want to use a node named something else apart from "tools",
    # You can update the value of the dictionary to something else
    # e.g., "tools": "my_tools"
)
# 节点入口
graph_builder.add_edge("tools","chatbot")
graph_builder.add_edge(START, "chatbot")


graph = graph_builder.compile(checkpointer=memory)

# 选择线程
config = {"configurable": {"thread_id": "1"}}
# 处理节点流
def stream_graph_updates(user_input: str):
    events = graph.stream(
        {"messages": [HumanMessage(content=user_input)]},
        config,
        stream_mode="values",
    )
    for event in events:
        if "messages" in event and event["messages"]:
            # 2. 💡 只在是 AI 回复或工具回复时才 pretty_print，避免重复打印用户自己说的话
            latest_message = event["messages"][-1]
            if latest_message.type in ["ai", "tool"]:
                latest_message.pretty_print()

# 执行循环
while True:
    try:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        stream_graph_updates(user_input)
    except:
        # fallback if input() is not available
        user_input = "What do you know about LangGraph?"
        print("User: " + user_input)
        stream_graph_updates(user_input)
        break
