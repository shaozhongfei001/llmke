# R15 检查点 NEXT

- 更新时间：2026-10-29 20:20
- run_id：R15-TL-20261029
- 决策：CONTINUE
- 当前候选：worktree `feature/R12-real-rag`，HEAD 见 git log（本轮新增 4 个提交）

## 1. 本轮已完成（均有实测证据）

| 项 | 内容 | 判据 |
|---|---|---|
| L0 | 工作树/HEAD/运行制品固定；排除两处误判（ss 无 pid、网关根路径 000） | NEXT.md §2 旧版 |
| F01/F02 | 写边 rank 由 (src,谓词,dst) 派生；删除伪反向边；消费者不再截取 VID | Nebula 对照实验 PASS：旧 1 条 / 新 2 条 |
| F10 | 评级推导增加"适用产品"前提；减项符号保留；歧义不推导 + join_audit | 组件反例 PASS：甲+30 / 丙-30 / 乙 0 |
| F04 | question_re 消费 `RetrievedData.getGlobalAnswer()`，global 无答案不回落 | 3.0s(失败) → 2.0s(status=2)，日志 R15-F04 |

证据目录：`platform/r12/qa/evidence/r15/{a02,a03,a09}/`

## 2. 本轮新发现（比原评审更深一层）

### A09 代次混存 —— 当前答案错的真正原因

```
问「智造贷最高额度」→ 答 1000 万（应 8000 万）
reduce 消费链路已通（F04 已修），但社区摘要里只有：
   人民币5000万元 -单户最高授信额度-> 智造贷
   人民币1000万元 -信用方式上限-> 智造贷
图里 8000 万不存在；5000 万来自 file_id=258（V0，status=0 已删除）
```

文件维度对照（这是最硬的一条）：

| file_id | 版本 | 文档状态 | graph_parse_status | 图中边数 |
|---|---|---|---|---|
| 258 | V0 | 已删 | 3 | 16 |
| 234 | V0 | 已删 | 3 | 4 |
| 328 | V1 | 有效 | 1（未解析） | 0 |
| 343 | V1 | 有效 | **3（成功）** | **0** |

⇒ 有效文件零边、已删文件有边；且 343「解析成功但零产出」没被拦。

### 阻塞点：Java graphParse 对 kb_9 恒返回 10001「知识库不存在」

```
4 种入参组合（fileIds 为 int/str、knowledgeBaseId 为 9/"9"、kbId）全部 404
knowledge_base 表：id=9 status=1 owner=admin；id=34 status=0 owner=admin
```

代码路径：`graphParse → knowledgeBaseDomainService.findByKbId(kbId)` 返回 null。
需确认 FilesParseReq 的字段绑定与 findByKbId 的查询条件（疑似字段名/状态过滤）。

## 3. 下一精确动作

```
N1  用 Python 图服务 /generate_triple_data 直接对 file 343 的 chunk 发起抽取
    （绕过 Java 入参问题，先证明"新写边逻辑在真实链路上产出单向、带 rank 的边"）
    通过：g_kb_9 中 file_id=343 的边数 > 0，且同一事实只有一个方向
    失败诊断：抽取侧对 pptx 文本是否产出三元组（W01 类型/过滤问题）

N2  修 Java graphParse 的「知识库不存在」：定位 FilesParseReq 绑定与 findByKbId 条件
    通过：kb_9 调 graphParse 返回 200 并建任务

N3  给解析成功判定加零产出闸门（gps=3 但 0 三元组 → 判失败/待复核）
    对应 A06、F09

N4  重建 g_kb_9：丢弃 status=0 文件的边，只保留有效文件代次
    对应 A09、A10；重建前先导出当前空间做回退点
```

## 4. 运行制品与风险

```
· 图解析服务 19529 已于 20:01 重启（新写边逻辑生效）
· 问答服务 18083 已于 20:08 重启（F04 生效）
· 网关 8088 仍 STALE_JAR（12.8h），本轮未改网关代码，发布前需重启
· g_kb_9 现有边全部来自已删 V0 文件；重建前任何 A03/A09 结论都不成立
· Nebula 端口 19669（非 9669）；nebula3 客户端只在 venvs/graph
```

## 5. 恢复入口

```
cd /home/szf/data/dev/llmke-r12
cat docs/r15/NEXT.md docs/r15/TASKS.yaml docs/r15/RESULTS.json
git log --oneline -6
```
