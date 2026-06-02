from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from dotenv import load_dotenv
import json

from langgraph.types import interrupt

load_dotenv()
class BasicToolNode:
    """A node that runs the tools requested in the last AIMessage."""

    def __init__(self, tools: list) -> None:
        self.tools_by_name = {tool.name: tool for tool in tools}

    def __call__(self, inputs: dict):
        if messages := inputs.get("messages", []):
            message = messages[-1]
        else:
            raise ValueError("No message found in input")
        outputs = []
        for tool_call in message.tool_calls:
            tool_result = self.tools_by_name[tool_call["name"]].invoke(
                tool_call["args"]
            )
            outputs.append(
                ToolMessage(
                    content=json.dumps(tool_result),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        return {"messages": outputs}
@tool
def human_assistance(query: str) -> str:
    """Request assistance from a human."""
    human_response = interrupt({"query": query})
    return human_response["data"]
# 工具
tavily_search = TavilySearch(max_results=2)
# 工具集合
tools = [tavily_search,human_assistance]
# 工具节点
tool_node = BasicToolNode(tools=tools)
print(tool_node)



