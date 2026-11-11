# 可复算事实（生成于 2026-10-24）

## 仓库
- HEAD: `69c4dac6f51fd237b0f9117da10310ee9e87ec32`
- 树: `a83f46dbc903a8101673d5bc70868999ac9ca86b`
- 提交总数（自 a9c2b43）: 100

## 门禁（最近一次实跑）
- `make framework-verify` → rc=0，**322 passed / 0 skipped**
- `make p0-gate` → **rc=2**（四项 P0 全 OPEN，如实阻断）
- `evidence-check r16` → PASS

## 批次（13 个）
- r10=DONE
- r11=SUPERSEDED
- r12=SUPERSEDED
- r13=SUPERSEDED
- r14=SUPERSEDED
- r15=SUPERSEDED
- r16=QA_PENDING
- r2=SUPERSEDED
- r3=SUPERSEDED
- r4=SUPERSEDED
- r5=SUPERSEDED
- r6=SUPERSEDED
- r7=SUPERSEDED
- r8=SUPERSEDED
- r9=SUPERSEDED

## 数据层
- 目标 schema：43 表 / 538 列（`schema-verify.sh` 0 处不一致）
- 本系统新增机制表：6 张（document_chunk、document_evidence、index_generation、index_generation_activation、index_write_lease、index_outbox）
- 遗留业务表：37 张，**本系统 0 使用**

## 参考系统
- Java：1003 文件 / 78,444 行 / 45 Controller / 575 端点 / 9 模块
- Python 算法服务：326 文件 / 37,772 行 / 12 个 llm 端点

## 说明
以上数字均可用 `01` 文档附录中的命令复算；"322 passed" 指技术门禁，不等于业务可用。
