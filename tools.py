
# 工具描述
tool_schemas =[
    # 查询天气工具
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称"
                    }
                },
                "required": ["city"]
            }
        }
    },
    # 计算工具
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "计算数学表达式并返回结果",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression":{
                        "type": "string",
                        "description":"需要计算的数学表达式，例如12 * 8 + 5"
                    },
                    "required": ["expression"]
                    },

            }
        }
    }
]
def get_weather(city: str):

    weather_data = {
        "北京": "晴天 25°C",
        "上海": "小雨 22°C"
    }

    return weather_data.get(city, "未知城市")


def calculate(expression: str):

    try:
        result = eval(expression)
        return str(result)

    except Exception as e:
        return f"计算错误: {str(e)}"
# 工具注册，最简单的
TOOLS = {
    "calculate":calculate,
    "get_weather":get_weather,
}
