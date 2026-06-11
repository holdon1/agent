
import os
import random
import time

from dotenv import load_dotenv
load_dotenv(verbose=True)
PRIMARY_MODEL = os.getenv("ZHIPU_MODEL_ID")
FALLBACK_MODEL = os.getenv("ZHIPU_MODEL_ID") # 兜底模型
BASE_DELAY_MS = 500
MAX_RETRIES = 10
MAX_CONSECUTIVE_529 = 3
ESCALATED_MAX_TOKENS = 64000
DEFAULT_MAX_TOKENS = 8000
MAX_RECOVERY_RETRIES = 3
CONTINUATION_PROMPT = (
    "Output token limit hit. Resume directly — "
    "no apology, no recap. Pick up mid-thought."
)
class RecoveryState:
    """Track recovery attempts across the loop."""
    def __init__(self):
        self.has_escalated = False
        self.recovery_count = 0
        self.consecutive_529 = 0
        self.has_attempted_reactive_compact = False #是否经历过重新压缩
        self.current_model = PRIMARY_MODEL

def retry_delay(attempt, retry_after=None):
    """
    Exponential backoff with jitter. Retry-After takes priority.
    指数退避抖动算法
    """
    # 遵循服务器调度，如果给出明确调度时间
    if retry_after:
        return retry_after
    # 指数退避算法：min(基础时间 * 2^重试次数，32000ms)，然后转换成s，用于后续sleep
    base = min(BASE_DELAY_MS * (2 ** attempt), 32000) / 1000
    # 抖动
    jitter = random.uniform(0, base * 0.25) # 随机抖动时间 （0，base*0.25）制造时间差，避免多个请求同时退避相同时间后继续同时发出请求
    return base + jitter


def with_retry(fn, state: RecoveryState):
    """Exponential backoff for transient errors (429/529).
    Non-transient errors are re-raised for the outer handler."""
    for attempt in range(MAX_RETRIES):# 重试
        try:
            result = fn() # 使用lamda表达式，将大模型api以匿名函数形式，交给with_retry管理器调用
            state.consecutive_529 = 0 # 重试成功，清空529错误计数
            return result
        except Exception as e:
            # 获取错误类名，以及错误信息
            name = type(e).__name__
            msg = str(e).lower()

            # 429 rate limit -> exponential backoff
            # 429退避时间
            if "ratelimit" in name.lower() or "429" in msg:
                delay = retry_delay(attempt)
                print(f"  \033[33m[429 rate limit] retry {attempt+1}/{MAX_RETRIES},"
                      f" wait {delay:.1f}s\033[0m")
                time.sleep(delay)
                continue

            # 529 overloaded -> exponential backoff + fallback model
            if "overloaded" in name.lower() or "529" in msg or "overloaded" in msg:
                state.consecutive_529 += 1
                if state.consecutive_529 >= MAX_CONSECUTIVE_529:
                    # 兜底模型
                    if FALLBACK_MODEL:
                        state.current_model = FALLBACK_MODEL
                        state.consecutive_529 = 0
                        print(f"  \033[31m[529 x{MAX_CONSECUTIVE_529}]"
                              f" switching to {FALLBACK_MODEL}\033[0m")
                    else:
                        state.consecutive_529 = 0
                        print(f"  \033[31m[529 x{MAX_CONSECUTIVE_529}]"
                              f" no FALLBACK_MODEL_ID configured, continuing retry\033[0m")
                # 退避时间
                delay = retry_delay(attempt)
                print(f"  \033[33m[529 overloaded] retry {attempt+1}/{MAX_RETRIES},"
                      f" wait {delay:.1f}s\033[0m")
                time.sleep(delay)
                continue

            # Not transient -> re-raise for outer try/except
            raise
    raise RuntimeError(f"Max retries ({MAX_RETRIES}) exceeded")


def is_prompt_too_long_error(e: Exception) -> bool:
    """Check whether an API error indicates prompt/context too long."""
    msg = str(e).lower()
    return (("prompt" in msg and "long" in msg)
            or "prompt_is_too_long" in msg
            or "context_length_exceeded" in msg
            or "max_context_window" in msg)


def reactive_compact(messages: list) -> list:
    """Emergency compact — teaching version keeps last N messages.
    Real CC generates a compact summary via LLM, then retries with
    the compacted message list. Teaching version simplifies to tail
    retention since s08/s09 already cover LLM-based compact."""
    print("  \033[31m[reactive compact] trimming to last 5 messages\033[0m")
    tail = messages[-5:]
    return [{"role": "user",
             "content": "[Reactive compact] Earlier conversation trimmed. "
                        "Continue from where you left off."}, *tail]
