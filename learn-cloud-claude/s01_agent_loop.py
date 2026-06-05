import json
from pathlib import Path

from zai import ZhipuAiClient
import os
from dotenv import load_dotenv
from s02_tool_use import TOOLS,TOOL_HANDLERS
from s04_hooks import HOOKS,trigger_hook

load_dotenv()
# 大模型客户端
client = ZhipuAiClient(api_key=os.getenv("ZHIPU_API_KEY"))
MODEL = os.getenv("ZHIPU_MODEL_ID")
SYSTEM_PROMPT = f"""
You are a coding agent at {os.getcwd()}.

Before any multi-step task:
1. Create a todo list using todo_write.
2. Execute tasks using available tools.

IMPORTANT:
- Never output shell commands as text.
- If a command needs to run, call the bash tool.
- If a file needs reading, call read_file.
- If a file needs writing, call write_file.
- Continue until the task is completed.
- Do not stop after creating todos.
"""
rounds_since_todo = 0
# agent核心循环
def agent_loop_with_openai(messages:list):
    global rounds_since_todo
    while True:
        # 大模型回复
        print(f"TOOLS:{TOOLS}")
        # 大模型回忆当前任务
        if rounds_since_todo >= 3 and messages:
            messages.append({"role": "user",
                             "content": "<reminder>Update your todos.</reminder>"})
            rounds_since_todo = 0 # 计数器清0

        response = client.chat.completions.create(model=MODEL,tools=TOOLS,messages=messages,max_tokens=200)
        print(f"response:{response}")
        response_choice = response.choices[0]
        # 追加到消息列表
        # messages.append({"role":"assistant","content":response_choice.message.content})
        messages.append(response_choice.message)
        # 是否使用工具
        if not response_choice.message.tool_calls:
            # 触发退出事件
            result = trigger_hook("Stop",messages)
            if result is not None:
                messages.append({
                    "role":"user",
                    "content":str(result),
                })
            return response_choice.message.content

        rounds_since_todo += 1 # 调用大模型，计数加一

        # 获取工具，工具名，工具参数
        tool_call = response_choice.message.tool_calls[0]
        print(f"tool_call:{tool_call}")
        tool_name = tool_call.function.name # 工具名
        print(f"tool_name:{tool_name}")
        tool_input = json.loads(tool_call.function.arguments) # 工具参数
        print(f"tool_input:{tool_input}")
        # 调用工具前出发hook事件
        # 如果是权限校验，触发事件后返回的是拒绝的理由则跳过循环不执行工具调用，如果什么都不返回则继续工具调用
        result = trigger_hook("PreToolUse", tool_call)
        if result is not None :
            messages.append({
                "role":"tool",
                "content":str(result),
                "tool_call_id":tool_call.id,
            })
            continue

        # 调用工具得到结果
        handler = TOOL_HANDLERS[tool_name]
        output = handler(**tool_input) if handler else f"Unknown: {tool_name}"
        print(f"output:{output[:200]}")

        # 调用工具后出发工具事件
        trigger_hook("PostToolUse", tool_call,output)

        # 如果调用 todo_write 计数清0
        if tool_name == "todo_write":
            rounds_since_todo = 0

        # 工具调用结果追加到messages
        messages.append({
            "role":"tool",
            "content":output,
            "tool_call_id":tool_call.id,
        })


