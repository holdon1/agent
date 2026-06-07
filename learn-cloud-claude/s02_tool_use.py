import ast
import json
import os
import subprocess
from pathlib import Path

from tavily import TavilyClient
from dotenv import load_dotenv
load_dotenv()
# 工具定义
TOOLS = [
    # bash
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a shell command.",
            "parameters": {"type": "object",
                "properties": {
                    "command": {
                        "type": "string"
                    }
                },
                "required": ["command"]
            }
        }
    },
    # read_file
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "read a file.",
            "parameters": {"type": "object",
                "properties": {
                    "path": {
                        "type": "string"
                    },
                    "limit": {
                        "type": "integer"
                    }
                },
                "required": ["path"]
            }
        }
    },
    # write_file
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file.",
            "parameters": {"type": "object",
                "properties": {
                    "path": {
                        "type": "string"
                    },
                    "content":{
                        "type": "string"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    # edit_file
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace exact text in a file once.",
            "parameters": {"type": "object",
                "properties": {
                    "path": {
                        "type": "string"
                    },
                    "old_text":{
                        "type": "string"
                    },
                    "new_text":{
                        "type": "string"
                    }
                },
                "required": ["path", "old_text", "new_text"]
            }
        }
    },
    # glob
    {
        "type": "function",
        "function": {
            "name": "glob",
            "description": "Find files matching a glob pattern.",
            "parameters": {"type": "object",
                "properties": {
                    "pattern": {
                        "type": "string"
                    },

                },
                "required": ["pattern"]
            }
        }
    },
    # tavily_search
    {
        "type": "function",
        "function": {
            "name": "tavily_search",
            "description": "search for llm.",
            "parameters": {"type": "object",
                "properties": {
                    "query": {
                        "type": "string"
                    },
                    "max_results": {
                        "type": "integer"
                    }
                },
                "required": ["query"]
            }
        }
    },
    # todo_write
    {
        "type": "function",
        "function": {
            "name": "todo_write",
            "description": "Create and manage a task list for your current coding session.",
            "parameters": {
                "type": "object",
                "properties": {
                    "todos": {
                        "type": "array",
                        "description": "List of tasks.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "status":{"type": "string",
                                          "enum":["pending","in_progress","completed"]}

                            },
                            "required": ["content","status"]
                        }
                    },
                },
                "required": ["todos"]
            }
        }
    },
    # task
    {'type': 'function',
     'function': {
         'name': 'task',
         'description': '"Launch a subagent to handle a complex subtask. Returns only the final conclusion.',
         'parameters': {
             'type': 'object',
             'properties': {
                 'description': {
                     'type': 'string'
                 }
             },
             'required': ['description']
         }
     }
     },
    # load_skill
    {'type': 'function',
     'function': {
         'name': 'load_skill',
         'description': ' get full skill details when needed',
         'parameters': {
             'type': 'object',
             'properties': {
                 'name': {
                     'type': 'string'
                 }
             },
             'required': ['name']
         }
     }
     }
]
WORKDIR = Path.cwd()
def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path

# 工具执行
def run_bash(command: str) -> str:
    """进行文档综合操作"""
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=os.getcwd(),
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except (FileNotFoundError, OSError) as e:
        return f"Error: {e}"

def run_read(path, limit=None):
    """读文件"""
    lines = safe_path(path).read_text().splitlines()
    if limit:
        lines = lines[:limit]
    return "\n".join(lines)

def run_write(path, content):
    """写文件"""
    safe_path(path).write_text(content)
    return f"Wrote {len(content)} bytes to {path}"

def run_edit(path, old_text, new_text):
    """修改文件"""
    text = safe_path(path).read_text()
    if old_text not in text:
        return "Error: text not found"
    safe_path(path).write_text(text.replace(old_text, new_text, 1))
    return f"Edited {path}"

def run_glob(pattern):
    import glob as g
    return "\n".join(g.glob(pattern, root_dir=WORKDIR))
# to_do_write
CURRENT_TODOS: list[dict]=[] # 当前任务列表
def _normalize_todos(todos):
    if isinstance(todos, str):
        try:
            todos = json.loads(todos)
        except json.JSONDecodeError:
            try:
                todos = ast.literal_eval(todos)
            except (SyntaxError, ValueError):
                return None, "Error: todos must be a list or JSON array string"
    if not isinstance(todos, list):
        return None, "Error: todos must be a list"
    for i, t in enumerate(todos):
        if not isinstance(t, dict):
            return None, f"Error: todos[{i}] must be an object"
        if "content" not in t or "status" not in t:
            return None, f"Error: todos[{i}] missing 'content' or 'status'"
        if t["status"] not in ("pending", "in_progress", "completed"):
            return None, f"Error: todos[{i}] has invalid status '{t['status']}'"
    return todos, None
def run_todo_write(todos: list) -> str:
    global CURRENT_TODOS
    todos, error = _normalize_todos(todos)
    if error:
        return error
    CURRENT_TODOS = todos
    lines = ["\n\033[33m## Current Tasks\033[0m"]
    for t in CURRENT_TODOS:
        icon = {"pending": " ", "in_progress": "\033[36m▸\033[0m", "completed": "\033[32m✓\033[0m"}[t["status"]]
        lines.append(f"  [{icon}] {t['content']}")
    print("\n".join(lines))
    return f"Updated {len(CURRENT_TODOS)} tasks"
# tavily
client = TavilyClient(os.getenv("TAIL_API_KEY"))
def tavily_search(query:str,max_results:int=5):
    """搜索引擎工具"""
    result = client.search(query=query,max_results=max_results)
    return str(result)

from s06_sub_agent import spawn_subagent
from s07_skills import load_skill
# 工具映射
TOOL_HANDLERS={
    "bash":run_bash,
    "read_file":run_read,
    "write_file":run_write,
    "edit_file":run_edit,
    "glob":run_glob,
    "tavily_search":tavily_search,
    "todo_write":run_todo_write,
    "task":spawn_subagent,
    "load_skill":load_skill,
}


if __name__ == '__main__':
    from utils.function_to_schema import function_to_schema
    from s07_skills import load_skill
    pass

