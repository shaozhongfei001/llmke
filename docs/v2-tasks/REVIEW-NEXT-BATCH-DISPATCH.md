# 下一批派发（2026-11-03，T-A 复核后）

依据：评审方《LLMKE_T-A自证复核_20261103.md》（`/home/szf/data/dsh/graph-rag/`）。
本批只做**后端/图侧**；前端项（T-A5 高亮、引用入口、图谱增强页）归前端会话。

## T-B1：B01 落地 V2（方案已有，只做 M1–M3，不做清库）

- `git apply /tmp/b01-full.patch`（或 format-patch 自 0bac08a）→ 28 tests → 全量回归
  （失败集合与迁移前一致，+28 passed）。
- 落库后记 `PAIR_KEY_SCHEME=b01-ontology-directed-v1` 进 report；V2 树 `graph_types.py` 的旧
  `sorted()` 实现必须消失。
- **不清库重写**（需要“写入冻结 + 授权 + Nebula 客户端”，列为 T-B2 待批，不冒充已完成）。
- 证据：`docs/v2-tasks/evidence/B1-landed.md`（apply 输出 + 28 passed + 全量回归尾行 + diff 指纹）。

## T-A6 收口：产品链路 seeds 透传

- retrieval_shim 请求体加 `seeds`（来源：Java/检索侧种子识别结果，先透传后验证来源）；
- 页面级 A/B 对照（同 T-A2 判据）产出产品链路 GRAPH trace；
- `capabilities.retrieve_graph_route` note 更新（从“仅引擎直连”升级为“产品链路”，或保持 scope 并写缺项）。
- 证据：`docs/v2-tasks/evidence/A6-product-seeds.md`。

## T-A7 收口：业务语料社区五跳

- 用真实上传文档（非 F001–F012）重建快照，跑 `scripts/v2_a3_lineage_probe.py` 同款五跳；
- 输出与 A3 同构（五跳闭合 + sha256 + invalid=0 + 孤点保留）。
- 证据：`docs/v2-tasks/evidence/A7-business-lineage.md`。

## T-F1：证据修正（评审 P1/P2/P3 逐条关）

1. `A1-open-original.md` 口径统一：T-A1=D7a VERIFIED（不含高亮），删/改 §11.7、§12.3 矛盾句（P1-1）。
2. presign/previewStream 补 HAR 导出或“授权复跑一次页面 E2E”的记录（P1-2）。
3. `CHECKPOINT.md` 同步到本批（P2-1）。
4. 四张失败截图移入 `screenshots_negative/`（P2-2）。
5. 测试遗留数据（kb_1001/1002/1003、999017/999018/999019）清理方案，待授权执行（P3-1）。

## D9 补登记（顺手，已在 A2 里做了大半）

- api.py 已默认安装中文补丁（`_ensure_cjk_compat` + `health.cjk_compat`）→ 把“升级 HippoRAG 后重验中文补丁”
  写入交付/升级流程文档并登记；capabilities/D9 状态更新。

## 评审方并行（只读）

- 更新达成度核对：D7a 成立、D6 引擎级成立、D4 夹具级成立、D9 部分（默认装补丁已落地）。
- 下一包复核：T-B1/T-A6/T-A7/T-F1 的每条证据复跑交叉核对。

## 提交纪律（立即生效，跨会话单写者规则）

1. **TL 提交只 add 本批次文件**：`services/rag-alg/index_data_service/index_graph_service/graph_types.py`、
   `tests/test_graph_direction_b01.py`、`docs/v2-tasks/**`。**禁止 `git add -A` / `git commit -am`**。
2. 提交前必须 `git status --short` 确认：`frontend/plateform/src/**` 下 4 个在途文件
   （`AiInputer/common/services/apis.tsx`、`AiInputer/common/services/servers.ts`、
   `AIChat/components/DrawerPreview.tsx`、`AIChat/index.tsx`）**不得卷入任何后端提交**。
3. **前端会话**：立即 `git commit` 自己的 4 个文件（或切独立分支）；在提交落地前，
   任何其他会话不得碰这些文件。跨会话规则全文见 `docs/v2-tasks/CROSS-SESSION-RULES.md`。
