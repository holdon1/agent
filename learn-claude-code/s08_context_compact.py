import json
import os
import time
from pathlib import Path

from dns.rdtypes.ANY.L32 import L32
from scipy.ndimage import histogram
from wasabi import msg
from zai import ZhipuAiClient
from dotenv import load_dotenv
from s02_tool_use import summarize_history,write_transcript
load_dotenv()
CONTEXT_LIMIT = 50000
KEEP_RECENT = 3
PERSIST_THRESHOLD = 30000

def estimate_size(msgs): return len(str(msgs))

def _block_type(block):
    return block.get("type") if isinstance(block, dict) else getattr(block, "type", None)

def _message_has_tool_use(msg):
    """消息中是否有工具调用消息"""
    if msg.get("role") != "assistant":
        return False
    tool_calls = msg.get("tool_calls")
    if not tool_calls:
        return False
    return len(tool_calls) > 0


def _is_tool_result_message(msg):
    """消息中是否有工具结果"""
    if isinstance(msg, dict):
        return msg.get("role") == "tool"
    return getattr(msg, "role", None) == "tool"
# L1
def snip_compact(messages,max_messages=50):
    """保留messages中前三条和后四十七条信息"""
    # 检查messages数量，是否需要压缩
    if len(messages) < max_messages:
        return messages
    # 开始划分 前3 后47
    keep_head, keep_tail = 3, max_messages-3
    head_end, tail_start = keep_head, len(messages)-keep_tail
    # 修复边界 前边界最后一条，后边界第一条（完整的工具链调用）
    if head_end > 0 and _message_has_tool_use(messages[head_end-1]):
        while head_end < len(messages) and _is_tool_result_message(messages[head_end]):
            head_end += 1
    if (tail_start > 0 and tail_start < len(messages)
            and _is_tool_result_message(messages[tail_start])
            and _message_has_tool_use(messages[tail_start - 1])):
        tail_start -= 1
    # 修复边界后判断 前边界和后边界是否有重合，存在重合则不需要压缩
    if head_end >= tail_start:
        return messages
    # 删除中间区域
    snipped = tail_start - head_end
    # 插入占位符并返回压缩后的消息
    return messages[0:head_end] + [{"role": "user", "content": f"[snipped {snipped} messages]"}] + messages[tail_start:]

# L2
KEEP_RECENT_TOOL_RESULTS = 3
def _collect_tool_results(messages):
    """获取上下文中的工具调用索引集"""
    tool_results = []
    for index,msg in enumerate(messages):
        if msg.get("role") == "tool":
            tool_results.append((index,msg))
    return tool_results
def micro_compact(messages):
    """使用占位符将旧的工具结果替换，节省上下文容量"""
    tool_results = _collect_tool_results(messages)
    if len(tool_results) <= KEEP_RECENT_TOOL_RESULTS:
        return messages

    old_tool_results = tool_results[:-KEEP_RECENT_TOOL_RESULTS] # 切牌索引，与原列表共享元素引用
    for _,msg in old_tool_results:
        content = msg.get("content","")
        if isinstance(content, str) and len(content) > 120:
            msg["content"] = (
                "[Earlier tool result compacted. "
                "Re-run the tool if needed.]"
            )
    return messages

# L3
MAX_TOOL_BYTES = 200_000 # 最后一次工具调用结果阈值
TOOL_RESULTS_DIR = Path(".tool_results")
def persist_large_output(tool_call_id: str, output: str) -> str:
    """
    超大输出写入磁盘，只保留摘要。
    """
    if len(output) <= PERSIST_THRESHOLD:
        return output

    TOOL_RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    path = TOOL_RESULTS_DIR / f"{tool_call_id}.txt"

    if not path.exists():
        path.write_text(output, encoding="utf-8")

    return (
        f"[Large output persisted]\n"
        f"File: {path}\n"
        f"Preview:\n"
        f"{output[:2000]}"
    )
def tool_result_budget(tool_message):
    """
    控制最新一轮对话 tool message 的总大小。
    """
    total_size = sum(
        len(str(msg.get("content", "")))
        for msg in tool_message
    )

    if total_size <= MAX_TOOL_BYTES:
        return

    ranked = sorted(
        tool_message,
        key=lambda m: len(str(m.get("content", ""))),
        reverse=True,
    )

    for msg in ranked:
        if total_size <= MAX_TOOL_BYTES: # 总大小低于阈值
            break

        content = str(msg.get("content", ""))

        if len(content) <= PERSIST_THRESHOLD: # 单个工具调用结果低于单条工具结果阈值
            continue

        tool_call_id = msg.get("tool_call_id","unknown")

        old_size = len(content)
        msg["content"] = persist_large_output(tool_call_id,content)

        new_size = len(msg["content"])
        total_size -= (old_size - new_size) # 更新总大小



# fallback 兜底策略
def reactive_compact(messages):
    transcript = write_transcript(messages)
    summary = summarize_history(messages)
    tail_start = max(0, len(messages) - 5)
    if _is_tool_result_message(messages[tail_start]) and _message_has_tool_use(messages[tail_start - 1]):
        tail_start -= 1
    return [{"role": "user","content": f"[Reactive compact]\n\n{summary}"}, *messages[tail_start:]]
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
    print(tool_result_budget(messages))


