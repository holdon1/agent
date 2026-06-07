import os

from s01_agent_loop import agent_loop_with_openai,SYSTEM
from s04_hooks import trigger_hook

if __name__ == '__main__':
    # 调用agent_loop
    SYSTEM = SYSTEM
    print(f"SYSTEM:{SYSTEM}")

    # messages=[{"role":"system","content":SYSTEM_PROMPT},
    #           {"role":"user","content":"执行命令 pwd"}]
    history = [{"role":"system","content":SYSTEM}]
    while True:
        try:
            query = input("\033[36ms02 >> \033[0m")
            trigger_hook("UserPromptSubmit",query)
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        final_answer = agent_loop_with_openai(history) # 主循环
        print(f"✅:{final_answer}")


