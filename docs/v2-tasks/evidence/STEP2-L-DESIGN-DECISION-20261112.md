# STEP2-L 设计判定书（T-D2MD-17 / 2026-11-12）

> 背景：Owner 反馈「人类对技术细节理解度/覆盖度难把握，期望由 AI 替做设计判定，而不是反复询问、理解」。
> **本文件性质**：由 `integration-agent` 作出的**技术判定**，**默认执行、可推翻**；不是 Owner 业务裁定，不代签 Owner 决议、不代签独立 QA。
> 工作方式变更：今后技术细节由本角色收敛成「判定 + 依据 + 默认动作」，不再把选项清单与代码行号摊给 Owner 逐项理解后选择。仅 §六 三类事项才升级给 Owner，且只需「是/否」或授权，不需要技术判断。

---

## 一、D-1（语义，事实判定）：`graph_root` ≠ 一个库

**判定**：`graph_root` 是容纳多个库的**落盘根 / 环境命名空间**；**`kb` / `kb_id` 才是「一个库」**。两者不得混用，文档与代码措辞以此为准。

依据：`02-CONTRACTS.md:24`（值为绝对目录）；实测同一 root 下有 `kb_9`(46/11)、`kb_1004`(4520 块)、顶层单快照(3 块)；`delta_build.py:51-58` `_kb_root(kb, root) = <root>/<kb>`；`api.py:208-231` 注释「per-kb 布局…多库各自建图的落点」；契约字段表 `kb` = primitiveName。
可复跑：`tests/test_p6_graph_root_semantics.py::test_d1_*`（4 项全绿，见 §七）。

**推论**：「在特定领域图谱范围内检索」这个能力**已经存在**，由 `QueryRequest.kb` → `engine_for_kb` → `_resolve_snapshot` + `kb.json` 归属校验实现（`test_d2_kb_ownership_prevents_cross_kb_fallback`）。按库**灰度切读**是 `INGEST_READ_MODE`/`INGEST_READ_KBS`（路径 B），与 `root` 无关。

---

## 二、D-2（B-2）判定：**采用 (a)，否决 (b)**

**判定**：`POST /v2/graph/query kb=kb_9` 的 `NOT_BUILT` 由「重启 18094 并设 `LLMKE_V2_ROOT=<app graph-root>`」解决。**否决「`QueryRequest` 增 `root`（需 CR）」，该方案不进入 backlog。**

| 理由 | 依据 |
|---|---|
| 根因是 18094 未配 per-kb 模式，不是查询请求缺字段 | 纯函数实证：不设 `LLMKE_V2_ROOT` → `_resolve_snapshot('kb_9')=None`；设后 → 命中 `<app>/kb_9/snapshot-20261107212905-365431-g0`。`test_d2_missing_root_reproduces_not_built` 固化 |
| (a) 零代码、零契约变更，代码原生支持 | `api.py:188-189` `_root_dir()`、`_resolve_snapshot` 的 per-kb 分支 |
| (b) 与 `kb` 语义重复，且仍要改 `query` 路由 + 重启 18094 | `snapshot_for(kb)` 当前不传 root；`_resolve_snapshot` 已支持 root |
| (b) 把存储根/环境选择权下沉给查询方，破坏服务端隔离模型 | P2-L8：`INGEST_READ_*` 由服务端运行时开关控制、运行态零注入；`RUNTIME-SWITCHES.yaml` |
| (b) 契约成本实打实 | `QueryRequest` 在 `contracts/schema/llmke-document-pipeline-v2.json:1547`、`GraphQueryRequest` 在 `llmke-core.json:1212`，均无 `root`；加字段需合同源 → `make generate/check` → CR → 19532/Java 回放 |

**执行条件**：重启 18094 属生产窗口动作，需 §六 的窗口放行；本轮未重启。

---

## 三、D-3（写入侧）判定：**保留请求驱动，不回退 (A)**

**判定**：追认 STEP2-J 对 `kb_ingest_service.py` 的修正（service 路径按请求 `graph_root`/`graph_api` 绑定），**不回退为 env 驱动**。

理由：`P4-L13C-PLAN.md:29` 的硬性要求「C 段所有 ingest 请求必须显式带 `graph_root`」是 **fail-closed 设计**（`graph_root=None` 会默认落到线上图）；`FenceRevokeRequest` 更因「影子撤权写进生产 `fence.json`」事故要求显式 root。回退 (A) 会重新引入该风险。

**风险处置（接受并记录，不掩盖）**：当前无服务端白名单。基于可核实的信任边界接受该风险：
- 事实：`ss -ltnp` 显示 18096 仅监听 `127.0.0.1`；
- 事实：实际调用方是内部 `18097 kb_parse_service`（`ingest_url=http://127.0.0.1:18096/kb/ingest`）与人工/脚本；Java `v2-ingest.url: ""` 仍为关闭；均非终端用户。

**失效条件（触发即必须先补白名单）**：① 18096 暴露到非 loopback 或经网关对外；② 接入不可信调用方；③ Owner 要求对外提供摄取 API。届时新增开关须按 `RUNTIME-SWITCHES.yaml` 首行规则登记，错误码与兼容去向一并入 CR。

**如实留痕**：`P4-L13C-R0` 曾将 (A)/(B) 列为待 Owner 裁定且未见结论，STEP2-J 代选了 (B)；本判定予以追认并登记，不隐藏这一越位。

---

## 四、D-4 / D-5（范围判定）

- **D-4**：「按库灰度切读」= `INGEST_READ_MODE=snapshot` + `INGEST_READ_KBS=[kb_9]`（STEP2-F 路径 B，代码未实现）。**另立条目，不混入当前窗口，不因它阻塞 `T-D2MD-17`**：当前窗口只做「图根式切读 + 指纹验收」。
- **D-5**：`kb_1004/current.json.dir` 仍指向已删 `llmke-r12`（与 `kb_9` 同类的失效指针，实测设 root 后 `_resolve_snapshot('kb_1004')` 仍为 `None`）。登记为独立 backlog，**不在本次 P6 kb_9 范围扩大**。

---

## 五、D-6（协作方式判定）

1. 技术判定（语义、根因、方案取舍、实现与测试）由本角色作出并**默认执行**，附可复跑证据；Owner 可随时推翻，推翻后按「不删失败、留痕、回滚」处理。
2. 不再把「选项清单 + 代码行号 + 请你理解后选择」作为交付；交付形态是「判定 + 依据 + 默认动作 + 失效条件」。
3. 事实 / 推断 / 判断分离；判断必须标注可被什么证伪。
4. 防自我出错的机制（比「模型是否聪明」更可靠）：只读核证 → 可复跑命令 → 变异复验证明断言非空转 → 证据留痕 → 可回滚 → 不把工程候选说成正式门禁/QA 通过。

---

## 六、仅以下三类升级给 Owner（不需要技术理解，只需是/否或授权）

| 类型 | 说明 | 本轮状态 |
|---|---|---|
| ① 生产窗口放行 | 重启 18094 / 停 19531 / 重启 18096 / 写生产图根，属业务风险决定 | **待放行**；放行后按 §七 默认动作执行 |
| ② 方向性业务变更 | 扩大试点范围、改变业务语义、放宽已批准 BL/CR | 无 |
| ③ Owner 决议 / 独立 QA 签署 | 项目纪律禁止代签；G-4 独立 QA 主体/密钥仍缺失 | 未签、不声称 `QA_PASS` |

前两轮把「B-2 技术选型」也升级为 Owner 裁定是**过度升级**，本判定予以纠正：它是集成层技术判定，已由 D-2 结案。

---

## 七、执行状态与默认下一步

本轮（纯只读核实 + 单元测试）：
- 新增 `tests/test_p6_graph_root_semantics.py` → **4 passed**（`PYTHONPATH=services/rag-alg/index_data_service <hipporag-toolenv>/bin/python -m pytest tests/test_p6_graph_root_semantics.py -q`）。
- 与 STEP2-J 的回归合并口径：相关 4 文件 **98 passed**；本次新增 4 项后语义层共 4 项独立断言。
- 未改代码/契约/数据，未启动/停止/重启服务，`contracts/`、`generated/` 干净，8 端口 LISTEN；未 commit、未签 `QA_PASS`。

**默认下一步（窗口放行后自动执行，不再逐项询问）**：
1. 同步运行树 `kb_ingest_service.py`（发布树 `563be5a1…` → 运行树 `5a19cc16…`），让请求级 root 线上生效。
2. 按 D-2 重启 18094 并设 `LLMKE_V2_ROOT=<app graph-root>`；复跑 `POST /v2/graph/query kb=kb_9`，断言不再 `NOT_BUILT`。
3. 让 `LLMKE_KB_STATE` 指向 STEP2-J 派生的同源 state；停 19531 → 重启 18096 → POST 6 份 → 比对生产 `current.json` 的 `documents` / `fingerprint.files` 指纹。
4. 留证；待「提交一次 git」指令入库；`T-D2MD-18` 在 17 验收前不解锁。

---

## 八、可推翻点

Owner 若不同意任一判定，只需指出编号（D-1…D-6）与方向，本角色按新方向重做证据与实现，不争辩、不保留旧判定为既成事实。推翻 D-2 选择 (b) 时，需同步给出「查询方应能选择存储根/环境」的业务前提，本角色据此补白名单 + 合同源 + CR + 消费者回放。
