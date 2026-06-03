# 权限模块
# 风险等级
from enum import Enum

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import interrupt

from s02_tool_use import safe_path
from s01_agent_loop import AgentState
from langgraph.graph import StateGraph, END,START
class PermissionLevel(str,Enum):
    ALLOW= "ALLOW"
    DENY= "DENY"
    ASK= "ASK"
# 规则引擎
def check_permission(tool_name:str,args:dict):
    # 如果是bash工具
    if tool_name == 'bash':
        # 获取参数
        command = args.get("command","")
        dangerous = [
            "rm -rf /",
            "sudo",
            "shutdown",
            "reboot",
        ]
        # 校验
        if any(command in x for x in dangerous):
                return PermissionLevel.DENY
        if command.startswith("rm "):
            return PermissionLevel.ASK
    # 如果是run_系列工具，即文件操作
    if tool_name in ['run_read','run_write','run_edit','run_glob']:
        # 获取路径
        path = args.get("path","")
        # 校验路径
        try:
            safe_path(path)
        except:
            return PermissionLevel.DENY
    return PermissionLevel.ALLOW

# 审批状态，在状态节点中添加一个字段

# 权限节点
def permission_gate(agentState:AgentState):
    print("\n====== permission_gate ======")
    # 获取当前状态最新消息，一般是ai_message
    latest_ai_message = agentState["messages"][-1]
    if not latest_ai_message.tool_calls:
        return {}
    # 获取工具调用
    tool_call = latest_ai_message.tool_calls[0]
    # 获取权限校验字段
    level = check_permission(tool_name=tool_call["name"],args=tool_call["args"])

    if level == PermissionLevel.ALLOW:
        return {} # 不修改节点状态
    if level == PermissionLevel.DENY:
        return {"messages": [
        AIMessage(content="Permission denied")
    ]} # 修改节点状态
    # 审批
    if level == PermissionLevel.ASK:

        approval = interrupt({
            "tool": tool_call["name"],
            "args": tool_call["args"]
        })

        if approval:
            return {}

        return {
            "messages": [
                AIMessage(content="User rejected operation.")
            ]
        }
# 权限路由
def route_after_chatbot(agentState:AgentState):
    latest_ai_message = agentState["messages"][-1]
    if getattr(latest_ai_message,"tool_calls",None):
        return "permission"
    return END



