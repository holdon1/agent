import json

from zai import ZhipuAiClient
import os
from dotenv import load_dotenv
from s02_tool_use import TOOLS,TOOL_HANDLERS


load_dotenv()
# 大模型客户端
client = ZhipuAiClient(api_key=os.getenv("ZHIPU_API_KEY"))
MODEL = os.getenv("ZHIPU_MODEL_ID")
SYSTEM_PROMPT = f"You are a coding agent at {os.getcwd()}. Use bash to solve tasks. Act, don't explain."

# agent核心循环
def agent_loop_with_zhipu(messages:list):
    while True:
        # 大模型回复
        print(TOOLS)
        response = client.chat.completions.create(model=MODEL,tools=TOOLS,messages=messages,max_tokens=200)

        response_choice = response.choices[0]
        # 追加到消息列表
        # messages.append({"role":"assistant","content":response_choice.message.content})
        messages.append(response_choice.message)
        # 是否使用工具
        if not response_choice.message.tool_calls:
            return response_choice.message.content

        # 获取工具，工具名，工具参数
        tool_call = response_choice.message.tool_calls[0]
        tool_name = tool_call.function.name # 工具名

        tool_input = json.loads(tool_call.function.arguments) # 工具参数

        # 调用工具得到结果
        handler = TOOL_HANDLERS[tool_name]
        output = handler(**tool_input) if handler else f"Unknown: {tool_name}"
        print(f"output:{output[:200]}")
        # 工具调用结果追加到messages
        messages.append({
            "role":"tool",
            "content":output,
            "tool_call_id":tool_call.id,
        })


