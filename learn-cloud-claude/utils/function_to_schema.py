import inspect
from typing import get_type_hints

TYPE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def function_to_schema(func):
    """
    Python函数 -> OpenAI Function Calling Schema
    """

    sig = inspect.signature(func)
    hints = get_type_hints(func)

    properties = {}
    required = []

    for name, param in sig.parameters.items():

        param_type = hints.get(name, str)

        json_type = TYPE_MAP.get(param_type, "string")

        properties[name] = {
            "type": json_type
        }

        # 没有默认值 => 必填
        if param.default is inspect.Parameter.empty:
            required.append(name)

    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": func.__doc__ or "",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
    }


