import json
from pathlib import Path

from jsonschema_path.readers import PathReader

WORKDIR = Path.cwd()
_last_context_key = None
_last_prompt = None
# 提示词模版，使用字典把不同组件分开,每条的value都是一个函数，方便用来穿参（上下文参数）
PROMPT_SECTIONS = {
    "identity":
        lambda ctx: "You are a coding agent.",

    "workspace":
        lambda ctx: f"Workspace:\n{ctx['workspace']}",

    "tools":
        lambda ctx: f"Tools:\n{', '.join(ctx['enabled_tools'])}",

    "memory":
        lambda ctx: (
            f"Memories:\n{ctx['memories']}"
            if ctx.get("memories")
            else ""
        ),
}

def assemble_system_prompt(context: dict) -> str:
    """
    根据最新的上下文动态拼接字符串
    :param context:
    :return:
    """
    sections = []

    for renderer in PROMPT_SECTIONS.values():

        content = renderer(context)

        if content:
            sections.append(content)

    return "\n\n".join(sections)

def get_system_prompt(context: dict) -> str:
    """
    封装assemble_system_prompt，增加一次校验
    校验：检查当前上下文是否改变，只有发生改变才重新拼接字符串
    :param context:
    :return:
    """
    global _last_context_key, _last_prompt
    key = json.dumps(context, sort_keys=True, ensure_ascii=False, default=str)
    if key == _last_context_key and _last_prompt:
        return _last_prompt
    _last_context_key = key
    _last_prompt = assemble_system_prompt(context)
    return _last_prompt

from s09_memory import MEMORY_INDEX
from s02_tool_use import TOOL_HANDLERS
def update_context(context: dict, messages: list) -> dict:
    """
    获取上下文实时状态
    :param context:
    :param messages:
    :return:
    """
    memories = ""
    if MEMORY_INDEX.exists():
        content = MEMORY_INDEX.read_text().strip()
        if content:
            memories = content
    # 组装的上下文用于assemble_system_prompt函数
    return {
        "enabled_tools": list(TOOL_HANDLERS.keys()),
        "workspace": str(WORKDIR),
        "memories": memories,
    }

if __name__ == '__main__':
    context = {
        "workspace": "/Users/baylee/project",

        "enabled_tools": [
            "bash",
            "read_file",
            "write_file",
        ],

        "memories":
            "User prefers Python",

        "skills":
            "- python\n- git",

        "todos":
            "[ ] scan repo",
    }
