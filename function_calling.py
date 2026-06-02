# import json
#
# from openai import OpenAI
# import os
# from dotenv import load_dotenv
# load_dotenv()
# # 1.编写工具
# tools = [
#     {
#         "type": "function",
#         "function": {
#             "name": "get_weather",
#             "description": "查询指定城市天气",
#             "parameters": {
#                 "type": "object",
#                 "properties": {
#                     "city": {
#                         "type": "string",
#                         "description": "城市名称"
#                     }
#                 },
#                 "required": ["city"]
#             }
#         }
#     }
# ]
# # 2.获取LLM客户端
# client = OpenAI(base_url=os.getenv("LLM_BASE_URL"),api_key=os.getenv("LLM_API_KEY"))
# # 3.用户消息
# messages = [
#     {
#         "role": "user",
#         "content": "北京天气怎么样？"
#     }
# ]
# # 4.大模型根据提问，决定是否调用工具。输出结构化参数
# response = client.chat.completions.create(messages=messages,model=os.getenv("LLM_MODEL_ID"),tools=tools,tool_choice='auto')
#
# message = response.choices[0].message
# print("第一次输出")
# print(message)
# if message.tool_calls:
#     # 5.指定工具接受结构化参数，执行输出结构化回答并添加到消息中
#     tool_call = message.tool_calls[0] # 工具调用
#     tool_name = tool_call.function.name # 工具名
#     arguments = json.loads(tool_call.function.arguments)
#     print("\n模型决定调用工具：")
#     print(tool_name)
#     print(arguments)
#     def get_weather(city):
#         return f"{city}：28°C，晴天"
#
#     tool_result = get_weather(arguments["city"]) # 工具执行函数
#     print("\n工具执行结果：")
#     print(tool_result)
#
#     # 第一次输出消息，添加到历史消息
#     messages.append(message)
#
#     # 将工具调用结果添加到历史消息
#     messages.append({
#         "role": "tool",
#         "tool_call_id": tool_call.id,
#         "content": tool_result
#     })
# # 6.大模型根据工具回答进行推理返回自然语言回答。
# final_response = client.chat.completions.create(
#     model=os.getenv("LLM_MODEL_ID"),
#     messages=messages,
# )
#
# print(final_response.choices[0].message.content)
#
#
#
#
#
