"""回答段 LLM 配置解析：把"用哪个模型、哪个端点、哪把钥匙"从代码里挪出来。

原则：
- **代码里不出现密钥**，只出现"环境变量名"；键值由运行环境提供；
- 默认走 DeepSeek-V4.1-Flash（`deepseek-flash`），可用环境变量整体切回本地端点；
- 缺键时给**明确可读**的错误（说明该设哪个变量），不要在请求阶段报 401 让人猜；
- 任何日志/异常里都不打印键值，只打印键名与长度。

环境变量：
  LLMKE_ANSWER_PROVIDER   deepseek（默认）/ local
  LLMKE_ANSWER_API_BASE   默认 https://api.deepseek.com/v1
  LLMKE_ANSWER_MODEL      默认 deepseek-flash（DeepSeek-V4.1-Flash）
  LLMKE_ANSWER_KEY_ENV    默认 DSEEK_2026_SZF_KEY（存 key 的环境变量名）
  LLMKE_ANSWER_TIMEOUT    默认 120 秒
  LLMKE_ANSWER_MAX_TOKENS 默认 512
"""

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, Optional

SCHEMA = "llmke.answer-llm.v1"

DEFAULT_PROVIDER = "deepseek"
DEFAULT_BASE = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-flash"          # 名称即 DeepSeek-V4.1-Flash
DEFAULT_KEY_ENV = "DSEEK_2026_SZF_KEY"

LOCAL_BASE = "http://127.0.0.1:18092/v1"
LOCAL_MODEL = "qwen2.5-7b-instruct"


def _budget_from_env(env: Dict[str, str]):
    """按 `LLMKE_ANSWER_RATE` 造调用预算；未配置返回 None（保持原有行为）。

    懒加载：没配限流的部署不该因为"预算模块导入失败"而起不来。
    """
    raw = (env.get("LLMKE_ANSWER_RATE") or "").strip()
    if not raw:
        return None
    from .llm_budget import from_env
    return from_env(env)


def resolve(env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """解析出 {provider, base, model, key_env, key, timeout, max_tokens}；不打印 key。"""
    env = env if env is not None else os.environ
    provider = (env.get("LLMKE_ANSWER_PROVIDER") or DEFAULT_PROVIDER).strip().lower()

    if provider == "local":
        # 本地端点也要限流：它同样占 GPU/CPU、同样会把请求打爆。
        # 早先这里没有 budget 键，`LLMKE_ANSWER_RATE` 对 local **静默不生效**——
        # "配了没反应"比"不支持"更难查，所以两个分支保持一致。
        return {"schema": SCHEMA, "provider": "local", "base": LOCAL_BASE, "model": LOCAL_MODEL,
                "key_env": None, "key": None,
                "budget": _budget_from_env(env),
                "timeout": int(env.get("LLMKE_ANSWER_TIMEOUT", "120")),
                "max_tokens": int(env.get("LLMKE_ANSWER_MAX_TOKENS", "1024"))}

    base = (env.get("LLMKE_ANSWER_API_BASE") or DEFAULT_BASE).strip()
    model = (env.get("LLMKE_ANSWER_MODEL") or DEFAULT_MODEL).strip()
    key_env = (env.get("LLMKE_ANSWER_KEY_ENV") or DEFAULT_KEY_ENV).strip()
    # 密钥来源链：环境变量优先，`LLMKE_ANSWER_KEY_FILE` 指向的文件兜底。
    # 只加文件兜底、不改优先级——原来靠 env 的部署行为完全不变。
    key_file = (env.get("LLMKE_ANSWER_KEY_FILE") or "").strip() or None
    from .secret_source import SecretSource
    key = SecretSource.from_env(key_env, key_file, environ=env).get()
    return {"schema": SCHEMA, "provider": provider, "base": base, "model": model,
            "key_env": key_env, "key_file": key_file, "key": key,
            "budget": _budget_from_env(env),
            "timeout": int(env.get("LLMKE_ANSWER_TIMEOUT", "120")),
            "max_tokens": int(env.get("LLMKE_ANSWER_MAX_TOKENS", "1024"))}


def describe(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """可安全打印的摘要：只有键名与是否就绪，没有键值。"""
    cfg = cfg or resolve()
    key = cfg.get("key")
    budget = cfg.get("budget")
    return {"schema": cfg.get("schema"), "provider": cfg["provider"], "base": cfg["base"],
            "model": cfg["model"], "key_env": cfg.get("key_env"),
            "key_present": bool(key), "key_len": len(key) if key else 0,
            "ready": cfg["provider"] == "local" or bool(key),
            "budget": budget.describe() if hasattr(budget, "describe") else None}


def make_llm_call(cfg: Optional[Dict[str, Any]] = None, *,
                  retries: int = 2) -> Callable[..., str]:
    """返回 `llm_call(messages=..., **kw)`，签名与 `answer.assemble` 期望一致。

    只做三件事：拼 OpenAI 兼容请求、带鉴权、失败重试。**不吞错**：
    最后一次失败原样抛出，让调用方看到状态码与错误体（不含键值）。
    """
    cfg = cfg or resolve()
    if cfg["provider"] != "local" and not cfg.get("key"):
        raise RuntimeError(
            f"回答段缺少 API key：请设置环境变量 {cfg.get('key_env')}（值不入库、不打印）")

    url = f"{cfg['base'].rstrip('/')}/chat/completions"
    # 不能叫 budget：`_call` 内部已经用 `budget` 表示 max_tokens 预算，
    # 同名会让它变成 `_call` 的局部变量，外层赋值不可见 → UnboundLocalError。
    call_budget = cfg.get("budget")

    def _call(messages, **kw):
        # 限流按"一次回答"计数，不按重试计数：重试是同一次回答的一部分，
        # 把它也计进去会让"输出被截断→加倍预算重试"这条路径莫名触发限流。
        if call_budget is not None:
            call_budget.before_call()
        payload = {"model": kw.get("model", cfg["model"]), "messages": messages,
                   "temperature": kw.get("temperature", 0),
                   "max_tokens": kw.get("max_tokens", cfg["max_tokens"])}
        body = json.dumps(payload).encode()
        headers = {"Content-Type": "application/json"}
        if cfg.get("key"):
            headers["Authorization"] = f"Bearer {cfg['key']}"

        last_error = None
        budget = payload["max_tokens"]
        for attempt in range(retries + 1):
            try:
                payload["max_tokens"] = budget
                body_retry = json.dumps(payload).encode()
                req = urllib.request.Request(url, data=body_retry, headers=headers)
                with urllib.request.urlopen(req, timeout=cfg["timeout"]) as resp:
                    data = json.loads(resp.read())
                choice = (data.get("choices") or [{}])[0]
                content = (choice.get("message") or {}).get("content") or ""
                # 被截断的 JSON 拿去解析只会得到"格式错误"这种误导性结论，
                # 所以这里按 finish_reason 判定并**加倍预算重试一次**。
                if choice.get("finish_reason") == "length":
                    last_error = f"输出被截断（max_tokens={budget}）"
                    budget *= 2
                    if attempt < retries:
                        continue
                    raise RuntimeError(f"回答段输出被截断，重试后仍超预算（{budget}）")
                return content
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode(errors="replace")[:200]
                last_error = f"HTTP {exc.code}: {detail}"
                if exc.code in (401, 403):      # 鉴权错不重试，重试也没用
                    break
            except Exception as exc:  # noqa: BLE001
                last_error = f"{type(exc).__name__}: {exc}"
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"回答段调用失败（{cfg['provider']}/{cfg['model']}）：{last_error}")

    return _call
