"""背压（BACKPRESSURE）的上游可读化：把协调器的拒绝状态翻译成用户能看懂的提示。

为什么要有这个文件
    `RebuildCoordinator.request()` 积压满时返回
    `{"status": "BACKPRESSURE", "pending": N, "max_pending": M, "rejected": K, "hint": ...}`，
    其中 `hint` 是写给运维看的（"先排空再上传"）。上游/前端拿到这个结构只会看到一次
    失败的入库：不知道为什么、要等多久、要不要重新上传。这里只做"翻译"，不改协调器语义。

字段口径（以 rebuild_coordinator.py 真实代码为准，不是猜的）
    - `status`       固定字符串 "BACKPRESSURE"，只有它等于这个值才出文案；
    - `pending`      当前排队条数；
    - `max_pending`  排队上限（协调器构造参数，默认 200）；
    - `rejected`     累计被拒次数；
    - `retry_in_s`   **不在** BACKPRESSURE 响应里，只在 `coordinator.stats()` 里（退避剩余秒数），
                     所以是可选的：有就用，没有就给一个保守建议值并明说是"预计"。
    注意 `capacity` / `retry_after_s` 这两个名字在真实代码里并不存在。

不做的事：不改协调器的判定、不发告警、不排队、不估算真实完成时间。
"""

import math
from typing import Any, Dict, Optional

CODE = "REBUILD_BACKPRESSURE"
HTTP_STATUS = 429                 # Too Many Requests：语义是"稍后重试"，不是服务端故障
DEFAULT_RETRY_AFTER_S = 30        # 没有 retry_in_s 时的保守建议值，文案里必须写成"预计"


def _number(value: Any) -> Optional[float]:
    """容忍 int/float/数字字符串；给不出数就返回 None（宁可少写一个数，也不编）。"""
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def describe_backpressure(state: Any,
                          default_retry_after_s: int = DEFAULT_RETRY_AFTER_S
                          ) -> Optional[Dict[str, Any]]:
    """把 BACKPRESSURE 状态翻成 `{code, message_zh, retry_after_s, user_action}`。

    非 BACKPRESSURE 输入返回 None —— 不要给所有输入都硬编一句文案，
    否则上游会把"队列正常"也当成"被拒了"。
    """
    if not isinstance(state, dict) or state.get("status") != "BACKPRESSURE":
        return None

    pending = _number(state.get("pending"))
    cap = _number(state.get("max_pending"))
    queue = (f"当前排队 {int(pending)}，上限 {int(cap)}"
             if pending is not None and cap is not None else "当前排队已满")

    retry = _number(state.get("retry_in_s"))
    if retry is None or retry <= 0:
        retry = float(default_retry_after_s)
    retry_s = max(1, int(math.ceil(retry)))

    return {
        "code": CODE,
        "message_zh": (f"图谱重建排队已满（{queue}），本次上传没有进入重建队列："
                       f"这批文件尚未开始建图，检索结果暂时不含其中内容。"
                       f"预计 {retry_s} 秒后可重试；具体完成时间以任务状态为准。"),
        "retry_after_s": retry_s,
        "user_action": (f"无需修改文件内容，预计 {retry_s} 秒后重新提交即可；"
                        "若连续多次仍失败，请联系运维确认重建进度。"),
        "http_status": HTTP_STATUS,
    }
