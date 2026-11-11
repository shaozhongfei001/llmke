# 外部评审镜像归档（2026-11-02）

> 本文件是 `shaozhongfei001/llmke-v2-review`（private 评审镜像仓库）唯一 PR #1 正文的原文归档。
> 该仓库已于 2026-11-11 删除。删除前确认：它的两个分支
> `main`=`419a87d`、`design/v2-input-engine-adoption-20261030-2101`=`bb328761`
> 均为本仓 `main` 的祖先、独有提交 0，代码层面无需合并；
> 相对本仓缺失的 9 个文件是 Owner 授权下线的 `/commonSearch` 废弃件
> （`d9509936` 前端 8 个 KnowledgeSearch 组件、`104d00ff` `CommonSearchRequest.java`），
> 且 9/9 可从本仓 `main` 历史中的父提交取回。
>
> **正文内的数字（58 PASS、1753 条告警等）是 2026-11-02 快照状态，已过时，仅作历史记录。**
> 当前状态以 `docs/v2-tasks/CHECKPOINT.md` 与最新验收报告为准。

## PR 元数据

- 标题：外部评审：LLMKE V2 统一输入与图引擎（b2bae85，132 commits）
- 状态：closed、未 merge；head = `bb32876164af9adecc1be5521a076b2509046d46`，base = `main`（`419a87d`）
- 规模：133 commits / 344 files / +93275 −13195
- reviews 0、review comments 0、issue comments 0、tags 0、releases 0

## PR 正文原文

## 这是什么

LLMKE V2 的**外部评审对象**。本仓是评审镜像，不在此处开发。

- 基线 `main` = `419a87d`（原仓 `origin/main`）
- 评审分支 = `design/v2-input-engine-adoption-20261030-2101`
- 提交 `b2bae850bde7e8fdfb84b8cd099ef29bd59ce797`（2026-11-02）
- 规模：132 commits / 344 files（`docs 136、tests 66、scripts 58、services 56、contracts 11、generated 6`）
- 验收报告：`docs/design/unified-documents-v2/offline/q-acceptance-latest.json`
  当前 **58 PASS / 0 FAIL / 0 SKIP / 1 NOT_IMPLEMENTED**（唯一未实现项是 docx→pdf，缺 LibreOffice Writer，非代码缺失）

## 设计集

在原 6 份主干设计外，本轮补齐 4 份缺口设计（均为草案，参数为建议值）：
`07_BACKUP_AND_RECOVERY`、`08_CAPACITY_AND_PERFORMANCE`、`09_AUDIT_TRAIL`、`10_FRONTEND_INTERACTION`。

## 建议阅读顺序

1. `00_READ_ME_FIRST.md`
2. `docs/design/unified-documents-v2/01_UNIFIED_DESIGN_V2.md`
3. `docs/design/unified-documents-v2/06_STANDARD_INPUT_AND_GRAPH_ENGINE.md`（契约与引擎边界，最值得挑毛病）
4. `02_RECONCILIATION_AND_DECISIONS.md` / `03_CONTRACT_CHANGE_MATRIX.md`
5. `docs/NEXT.md`（进度与已知坑）
6. `docs/reviews/R14-EXTERNAL-REVIEW-20261029.md`（上一轮外部评审问题清单，可对照关闭情况）

## 代码入口

核心在 `services/rag-alg/index_data_service/graph_engine_adapter/`：

| 模块 | 职责 |
|---|---|
| `pipeline.py` | 检索编排（撤权 fence + 可选生效期/可见域后置过滤） |
| `engine_hipporag.py` | HippoRAG 引擎适配 |
| `rebuild.py` / `rebuild_coordinator.py` / `rebuild_scheduler.py` | 隔离快照重建、增量应用、调度与积压 |
| `lease.py` / `lease_mysql.py` | 跨机选主租约与 fencing |
| `assertions.py` / `normalize.py` / `mapping.py` | 断言层、归一、来源绑定 |
| `capabilities.py` | 能力声明与证据指向 |
| `export.py` / `retrieval_filter.py` / `canary.py` | 图导出、后置过滤、灰度切换 |

验收脚本 `scripts/v2_*.py`（45 个），测试 `tests/`（84 个）。

## 请重点看的四处

1. **增量重建语义**（`rebuild.py::apply_delta`）：语义是"增量抽取 + 全量重建图"，
   高相似语料上观测到"内容未变而检索排序变化"。是否可接受？是否应限制为纯新增场景？
2. **过滤方向**（`retrieval_filter.py`）：版本窗口 fail-open（无日期保留）、可见域 fail-closed（查不到即丢）。
   方向相反是有意的，请判断越权与误杀风险。
3. **能力声明与证据**（`capabilities.py`）：VERIFIED 是否都有可复核证据，是否存在"实现了但没接线"却标 VERIFIED。
4. **租约与 fencing**（`lease_mysql.py` / `rebuild_coordinator.py`）：能否真正阻止旧主晚到写入覆盖新快照。

## 已知边界（声明，不是 bug）

- `engine_version_filtering` / `engine_visibility_isolation` 仍是 **NOT_VERIFIED**：过滤在平台侧，引擎执行期与构建期均无约束
- 灰度结论不可外推到生产规模：语料仅 3～10 块
- 告警只验证到本地桩，无真实企业微信/钉钉网关
- doc2md 的 5 项 CLI-help 失败在另一仓库的他人分支，不在本仓范围
- `scripts/security_scan.py` 1 项失败、1753 条历史告警为既有问题（多为测试默认口令/示例连接串）

## 本地验证

```bash
export PYTHONPATH=services/rag-alg/index_data_service
python -m pytest tests/ -q          # Python 3.10；图引擎相关需 3.11 + 模型服务
```

无需 GPU；不依赖任何外部账号即可阅读与跑纯逻辑测试。
