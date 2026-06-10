import os

from s01_agent_loop import agent_loop_with_openai
from s04_hooks import trigger_hook
from s10_system_prompt import get_system_prompt,update_context
if __name__ == '__main__':
    # 调用agent_loop

    # messages=[{"role":"system","content":SYSTEM_PROMPT},
    #           {"role":"user","content":"执行命令 pwd"}]
    history = []
    context = update_context({}, history)
    while True:
        try:
            query = input("\033[36ms02 >> \033[0m")
            trigger_hook("UserPromptSubmit",query)
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break

        history.append({"role": "user", "content": query})
        final_answer = agent_loop_with_openai(history,context) # 主循环
        context = update_context(context, history)
        print(f"✅:{final_answer}")


