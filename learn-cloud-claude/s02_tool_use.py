import os
import subprocess
from pathlib import Path

from tavily import TavilyClient
from dotenv import load_dotenv
load_dotenv()
# 工具定义
TOOLS = [
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

]
WORKDIR = Path.cwd()
def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path

# 工具执行
def run_bash(command: str) -> str:
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

# tavily
client = TavilyClient(os.getenv("TAIL_API_KEY"))
def tavily_search(query:str,max_results:int=5):
    """搜索引擎工具"""
    result = client.search(query=query,max_results=max_results)
    return str(result)

# 工具映射
TOOL_HANDLERS={
    "bash":run_bash,
    "read":run_read,
    "write":run_write,
    "edit":run_edit,
    "glob":run_glob,
    "search":tavily_search
}