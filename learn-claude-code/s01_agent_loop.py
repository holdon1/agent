import json
from pathlib import Path

from zai import ZhipuAiClient
import os
from dotenv import load_dotenv
from s02_tool_use import TOOLS,TOOL_HANDLERS,compact_history
from s04_hooks import HOOKS,trigger_hook
from s07_skills import build_system
from s08_context_compact import snip_compact,micro_compact,tool_result_budget,reactive_compact,estimate_size,CONTEXT_LIMIT
from utils.collect_last_tool_results import collect_last_tool_results
from s09_memory import build_system_with_memory, load_memories, extract_memories, consolidate_memories
from s10_system_prompt import get_system_prompt,update_context
from s11_error_retry import with_retry, RecoveryState, is_prompt_too_long_error, ESCALATED_MAX_TOKENS, \
    CONTINUATION_PROMPT, MAX_RECOVERY_RETRIES, DEFAULT_MAX_TOKENS

load_dotenv()
# 大模型客户端
client = ZhipuAiClient(api_key=os.getenv("ZHIPU_API_KEY"))
MODEL = os.getenv("ZHIPU_MODEL_ID")

CONTEXT_LIMIT = CONTEXT_LIMIT
MAX_REACTIVE_RETRIES = 1  # retry limit for reactive compact
rounds_since_todo = 0
retryState = RecoveryState()
# agent核心循环
def agent_loop_with_openai(messages:list,context:dict):

    global rounds_since_todo
    reactive_retries = 0  # 兜底重试次数
    memories_content = load_memories(messages)
    memory_turn = len(messages) - 1 if messages and isinstance(messages[-1].get("content"), str) else None
    #===动态提示词拼接===
    system = get_system_prompt(context) # 初始化

    while True:
        messages = [{"role": "system", "content": system}] + messages
        # 大模型回复
        print(f"TOOLS:{TOOLS}")
        #====压缩上下文===
        # message快照，相当于当前messages备份
        pre_compress = [m if isinstance(m, dict) else {"role": m.get("role", ""),
                                                    "content": str(m.get("content", ""))} for m in messages]
        # 最后的工具调用结果集
        last_tool_results = collect_last_tool_results(messages)
        # L3
        if last_tool_results:
            tool_result_budget(last_tool_results)
        # L1
        messages[:] = snip_compact(messages)
        # L2
        messages[:] = micro_compact(messages)

        # 经过预处理messages依然超过上下文容量L4
        if estimate_size(messages) > CONTEXT_LIMIT:
            print("[auto compact ]")
            messages[:] = compact_history(messages)

        # 大模型回忆当前任务
        if rounds_since_todo >= 3 and messages:
            messages.append({"role": "user","content": "<reminder>Update your todos.</reminder>"})
            rounds_since_todo = 0 # 计数器清0
        request_messages = messages
        # 构造一个临时消息。
        if memories_content and memory_turn is not None and memory_turn < len(messages):
            request_messages = messages.copy()
            request_messages[memory_turn] = {
                **messages[memory_turn],
                "content": memories_content + "\n\n" + messages[memory_turn]["content"],
            }
        try:
            #======调用大模型======

            response = with_retry(lambda:client.chat.completions.create(model=MODEL,
                                                      tools=TOOLS,
                                                      messages=request_messages,
                                                      max_tokens=200),
                                                      retryState)
            reactive_retries = 0  # 大模型调用成功，重试次数清零
        except Exception as e:
            if is_prompt_too_long_error(e):
                if not retryState.has_attempted_reactive_compact:
                    messages[:] = reactive_compact(messages)
                    retryState.has_attempted_reactive_compact = True
                    continue
                print("  \033[31m[unrecoverable] still too long after compact\033[0m")
                messages.append({"role": "assistant", "content": [
                    {"type": "text",
                     "text": "[Error] Context too large, cannot continue."}]})
                return None
            # Unrecoverable
            name = type(e).__name__
            print(f"  \033[31m[unrecoverable] {name}: {str(e)[:100]}\033[0m")
            messages.append({"role": "assistant", "content": [
                {"type": "text", "text": f"[Error] {name}: {str(e)[:200]}"}]})
            return None
        # ── Path 1: max_tokens -> escalate or continue ──
        if response.choices[0].finish_reason == "max_tokens":
            # First escalation: don't append truncated output, retry same request
            # 步骤一：提高上下文俄额度
            if not retryState.has_escalated:
                max_tokens = ESCALATED_MAX_TOKENS
                retryState.has_escalated = True
                print(f"  \033[33m[max_tokens] escalating"
                      f" {DEFAULT_MAX_TOKENS} -> {ESCALATED_MAX_TOKENS}\033[0m")
                continue
            # 64K still truncated: save truncated output + continuation prompt
            messages.append({"role": "assistant", "content": response.content}) # 当次被截断的对话需要添加到上下位，这样模型才能继续续写
            if retryState.recovery_count < MAX_RECOVERY_RETRIES:
                messages.append({"role": "user", "content": CONTINUATION_PROMPT}) # 续写提示词
                retryState.recovery_count += 1
                print(f"  \033[33m[max_tokens] continuation"
                      f" {retryState.recovery_count}/{MAX_RECOVERY_RETRIES}\033[0m")
                continue
            print("  \033[31m[max_tokens] recovery limit reached\033[0m")
            return response.choices[0].message.content # 最终结果（如果超过续写次数，返回最后一次结果）

        print(f"response:{response}")
        response_choice = response.choices[0]
        # 追加到消息列表
        # messages.append({"role":"assistant","content":response_choice.message.content})
        # messages.append(response_choice.message)
        messages.append(
            {
                "role": "assistant",
                "content": response_choice.message.content,
                "tool_calls": response_choice.message.tool_calls,
            }
        )
        extract_memories(pre_compress)
        consolidate_memories()
        # 是否使用工具
        if not response_choice.message.tool_calls:
            # 触发退出事件
            result = trigger_hook("Stop", messages)
            if result is not None:
                messages.append({
                    "role": "user",
                    "content": str(result),
                })

            return response_choice.message.content

        rounds_since_todo += 1  # 调用大模型，计数加一

        # 获取工具，工具名，工具参数（可能调用多个工具）
        for tool_call in response_choice.message.tool_calls:
            print(f"tool_call:{tool_call}")
            tool_name = tool_call.function.name  # 工具名
            print(f"tool_name:{tool_name}")
            tool_input = json.loads(tool_call.function.arguments)  # 工具参数
            print(f"tool_input:{tool_input}")
            # 调用工具前出发hook事件
            # 如果是权限校验，触发事件后返回的是拒绝的理由则跳过循环不执行工具调用，如果什么都不返回则继续工具调用
            result = trigger_hook("PreToolUse", tool_call)
            if result is not None:
                messages.append({
                    "role": "tool",
                    "content": str(result),
                    "tool_call_id": tool_call.id,
                })
                continue

            # 调用工具得到结果
            handler = TOOL_HANDLERS[tool_name]
            output = handler(**tool_input) if handler else f"Unknown: {tool_name}"
            print(f"output:{output[:200]}")

            # 调用工具后出发工具事件
            trigger_hook("PostToolUse", tool_call, output)

            # 如果调用 todo_write 计数清0
            if tool_name == "todo_write":
                rounds_since_todo = 0

            # 工具调用结果追加到messages
            messages.append({
                "role": "tool",
                "content": output,
                "tool_call_id": tool_call.id,
            })

            # =====更新上下文和系统提示词=====
            context = update_context(context)
            system = get_system_prompt(context)





