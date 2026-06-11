def collect_last_tool_results(messages):

    results = []
    for msg in reversed(messages):

        if msg["role"] == "tool":
            results.append(msg)
        else:
            break
    results.reverse()
    return results
if __name__ == '__main__':
    messages = [
        {"role": "user", "content": "读取a.py"},

        {
            "role": "assistant",
            "tool_calls": [{"id": "call1"}]
        },

        {
            "role": "tool",
            "tool_call_id": "call1",
            "name": "read_file",
            "content": "A" * 300
        },

        {"role": "user", "content": "读取b.py"},

        {
            "role": "assistant",
            "tool_calls": [{"id": "call2"}]
        },

        {
            "role": "tool",
            "tool_call_id": "call2",
            "name": "read_file",
            "content": "B" * 300
        },

        {"role": "user", "content": "读取c.py"},

        {
            "role": "assistant",
            "tool_calls": [{"id": "call3"}]
        },

        {
            "role": "tool",
            "tool_call_id": "call3",
            "name": "read_file",
            "content": "C" * 300
        },

        {"role": "user", "content": "读取d.py"},

        {
            "role": "assistant",
            "tool_calls": [{"id": "call4"}]
        },

        {
            "role": "tool",
            "tool_call_id": "call4",
            "name": "read_file",
            "content": "D" * 300
        },
    ]

    print(len(collect_last_tool_results(messages)))