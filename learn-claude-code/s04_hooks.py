"""
由于权限校验等方法都要在主循环中发生作用，如果有多个类似方法放在主循环中，会导致主循环变得臃肿
因此，讲这些方法进行封装，用一个hook映射收集汇总这些函数，调用方法类似反射
hook的4个核心工作时期：query进去LLM前，工具发生作用前，工具发生作用后，主循环停止前。
其中，权限校验处于工具发生作用前

"""
import json
from pathlib import Path

WORKDIR = Path.cwd()
# 事件注册列表，事件名称映射回调列表
HOOKS = {
    "UserPromptSubmit":[],
    "PreToolUse":[],
    "PostToolUse":[],
    "Stop":[],
}

# 注册事件
def register_hook(event:str,callback):
    HOOKS[event].append(callback)

# 触发事件
def trigger_hook(event:str,*args):
    for callback in HOOKS[event]:
        result = callback(*args)
        if result is not None:
            return result
    return None

def context_inject_hook(query: str) -> str | None:
    """Inject current working directory info into every prompt."""
    print(f"\033[90m[HOOK] UserPromptSubmit: working in {WORKDIR}\033[0m")
    return None   # return None = no modification, let prompt through
# PreToolUse: 日志
def log_hook(tool_call):
    print(f"[HOOK] {tool_call.function.name}(...)")

from s03_permission import DENY_LIST,PERMISSION_RULES
def check_permission(tool_call):
    tool_name = tool_call.function.name
    tool_input = json.loads(tool_call.function.arguments)  # 工具参数
    if tool_name == "bash":
        for pattern in DENY_LIST:
            if pattern in tool_input.get("command", ""):
                return "Permission denied by deny list"
    if tool_name in ("write_file", "edit_file"):
        path = tool_input.get("path", "")
        if not (WORKDIR / path).resolve().is_relative_to(WORKDIR):
            choice = input("   Allow? [y/N] ").strip().lower()
            if choice not in ("y", "yes"):
                return "Permission denied by user"
    return None
# PostToolUse: 大文件提醒
def large_output_hook(tool_call, output):
    if len(str(output)) > 100000:
        print(f"[HOOK] ⚠ Large output from {tool_call.function.name}")
# Stop
def summary_hook(messages: list) -> str | None:
    """Print a summary when the loop is about to stop."""
    tool_count = sum(1 for m in messages
                     for b in (m.get("content") if isinstance(m.get("content"), list) else [])
                     if isinstance(b, dict) and b.get("type") == "tool_result")
    print(f"\033[90m[HOOK] Stop: session used {tool_count} tool calls\033[0m")
    return None   # return None = allow stop, return string = force continuation


register_hook("UserPromptSubmit", context_inject_hook)
register_hook("PreToolUse", check_permission)
register_hook("PreToolUse", log_hook)
register_hook("PostToolUse", large_output_hook)
register_hook("Stop", summary_hook)