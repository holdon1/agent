"""
1.先写Tool的四个核心组件
2.用户提问
3.获取大模型客户端
4.大模型接收提问并分析是否需要使用工具
5.假如需要：获取工具名，参数
6.通过Tool系统调用工具获取结果tool_result
7.结果回填，并再次调用大模型


"""
import json
from openai import OpenAI
import os
from dotenv import load_dotenv


from tools import tool_schemas, TOOLS

load_dotenv()

# 2.获取LLM客户端
client = OpenAI(base_url=os.getenv("LLM_BASE_URL"),api_key=os.getenv("LLM_API_KEY"))
# 历史信息
messages = [
    {
        "role": "system",
        "content": "你是一个智能助手"
    }
]

message ={
    "role": "user",
    "content":"帮我计算45 + 90"
}
 
messages.append(message)

response = client.chat.completions.create(
    model=os.getenv("LLM_MODEL_ID"),
    messages=messages,
    tools=tool_schemas,
    tool_choice="auto"
)

assistant_message = response.choices[0].message
messages.append(assistant_message)
print("第一次输出")
print(assistant_message)

if assistant_message.tool_calls:
    for tool_call in assistant_message.tool_calls:
        tool_name = tool_call.function.name
        tool_parameters = json.loads(tool_call.function.arguments)
        print(f"\n[Tool Call] {tool_name}")
        print(f"[Arguments] {tool_parameters}")

        # 路由选择，获取执行函数
        tool_function = TOOLS.get(tool_name)
        if not tool_function:
            tool_result = "工具不存在"
        else:
            tool_result = tool_function(**tool_parameters)

        print(f"[Tool Result] {tool_result}")
        # 回填 tool result
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": tool_result
        })

    second_response = client.chat.completions.create(model=os.getenv("LLM_MODEL_ID"),messages=messages)

    final_answer = second_response.choices[0].message

    messages.append(final_answer)

    print("\nAssistant:", final_answer.content)
