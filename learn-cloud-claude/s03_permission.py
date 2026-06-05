# 权限校验模块
# 拒绝列表，规则匹配，用户确认
# 发生在工具调用前，判断工具调用是否合法，不合法则取消此次调用。
import json
from pathlib import Path
# bash 工具设置DENY列表，如果大模型给出参数命中DENY列表直接拒绝执行
DENY_LIST = [    "rm -rf /", "sudo", "shutdown", "reboot",
                 "mkfs", "dd if=", "> /dev/sda",
            ]
def check_deny_list(command:str):
    for pattern in DENY_LIST:
        if pattern in command:
            return f"Blocked: '{pattern}' is on the deny list"
    return True


# write read bash 分别设置规则匹配，命中这些规则的需要用户手动确认（human in the loop）
WORKDIR = Path.cwd()
PERMISSION_RULES = [
    {
        "tools": ["write_file", "edit_file"],
        "check": lambda args: not (WORKDIR / args.get("path", "")).resolve().is_relative_to(WORKDIR),
        "message": "Writing outside workspace",
    },
    {
        "tools": ["bash"],
        "check": lambda args: any(kw in args.get("command", "") for kw in ["rm ", "> /etc/", "chmod 777"]),
        "message": "Potentially destructive command",
    },
]
def check_rules(tool_name:str,args:dict):
    for rule in PERMISSION_RULES:
        if tool_name in rule["tools"] and rule["check"](args):
            return rule["message"]
    return None

def ask_user(tool_name: str, args: dict, reason: str) -> str:
    print(f"\n⚠  {reason}")
    print(f"   Tool: {tool_name}({args})")
    choice = input("   Allow? [y/N] ").strip().lower()
    return "allow" if choice in ("y", "yes") else "deny"

def check_permission(tool_call) -> bool:
    tool_name = tool_call.function.name
    tool_input = json.loads(tool_call.function.arguments) # 工具参数
    # 闸门 1: 硬拒绝
    if tool_name == "bash":
        reason = check_deny_list(str(tool_input))
        if reason:
            print(f"\n⛔ {reason}")
            return False

    # 闸门 2 + 3: 规则匹配 → 用户审批
    reason = check_rules(tool_name, tool_input)
    if reason:
        decision = ask_user(tool_name, tool_input, reason)
        if decision == "deny":
            return False

    return True

if __name__ == '__main__':
    print(check_deny_list("rm -rf /"))