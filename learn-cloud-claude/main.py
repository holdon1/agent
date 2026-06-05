import os

from s01_agent_loop import agent_loop_with_zhipu


if __name__ == '__main__':
    # 调用agent_loop
    SYSTEM_PROMPT = f"""You are a coding agent at {os.getcwd()}.
                        You have access to a tool named bash.
                        When a shell command is needed,
                        you MUST call the tool.
                        Never write shell commands directly.
                        Always use tool calls,Act, don't explain."""

    messages=[{"role":"system","content":SYSTEM_PROMPT},
              {"role":"user","content":"执行命令 pwd"}]
    history = [{"role":"system","content":SYSTEM_PROMPT}]
    while True:
        try:
            query = input("\033[36ms02 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        final_answer = agent_loop_with_zhipu(history) # 主循环
        print(f"✅:{final_answer}")


