#!/usr/bin/env python3
"""A15 完整 KB 回归与资源（任务书 §5.2 A15）。

判据：C01–C20 及原必选扩展实际使用流程成立；无空结果/跳过假绿；真实模型参与；资源可复算。
写操作边界：完整回归（上传/解析/重建/24h 观察/容量实验）不在本断言集范围，如实 SKIP。
只读快速核对（防止"整套流程其实跑在空数据上"）：
  N1 四个存储面的计数必须都 > 0（文件台账、ES 正文、社区摘要、Nebula 可见边）
  N2 计数之间必须自洽：图边来源文件 ⊆ 生效文件；社区来源文件 ⊆ 生效文件
  N3 问答必须由真实模型产出（答案非空且耗时 > 1s；0.0s 说明命中缓存/未真正推理）
"""
import collections

import common as C

ID = "A15"
TITLE = "完整 KB 回归与资源：四存储面非空且自洽、真实模型参与"
WRITES = True


def run():
    checks = []
    active = C.active_fids()
    led = C.ledger()
    d = C.es_search(C.KB, {"query": {"match_all": {}}}, size=1)
    n_docs = d["hits"]["total"]["value"]
    comms = C.communities()
    vis = [e for e in C.edges() if e["sf"] == "1"]

    counts = {"生效文件": len(active), "台账全部": len(led), "ES正文": n_docs,
              "社区摘要": len(comms), "可见边": len(vis)}
    checks.append(C.chk("N1 反例：四个存储面都非空", all(v > 0 for v in counts.values()),
                        f"计数={counts}（任一为 0 即「空跑」）"))

    efid = collections.Counter(e["fid"] for e in vis if e["fid"] not in active)
    cfid = {}
    for c in comms:
        bad = [str(x) for x in ((c["meta"] or {}).get("file_ids") or []) if str(x) not in active]
        if bad:
            cfid[c["es_id"]] = bad
    checks.append(C.chk("N2 反例：图与社区的来源文件都在生效集合内",
                        not efid and not cfid,
                        f"图侧越界={dict(efid)}；社区侧越界={cfid}"))

    a = C.ask("智造贷最高额度是多少？")
    checks.append(C.chk("N3 反例：真实模型参与（答案非空且耗时 > 1s）",
                        len(a["answer"].strip()) > 10 and a["elapsed"] > 1.0,
                        f"http={a['http']} 耗时={a['elapsed']}s 答案={a['answer'][:100]!r}"))

    return C.verdict(ID, TITLE, checks, writes=WRITES,
                     skip_reason="C01–C20 完整回归、容量/持续运行（原 24h 观察）不在本断言集范围，需另行执行")
