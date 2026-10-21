# 工作区迁移执行记录 V1.0

- 日期：2026-10-21
- 依据：`docs/integration/DOC2MD-WORKSPACE-DECISION.md`（决策 `INT-2026-10-21-WORKSPACE`）
- 执行人：Tech Lead
- 本文件位于 `docs/baseline/validation/`（不参与源码快照），写入不会使门禁证据失效

## 1. 迁移前锚点（已核对）

| 项 | 值 |
|---|---|
| doc2md HEAD | `d9e4f9831f77b8f2d2ab33ead6a744c2562fe39d`（`main`） |
| 未提交改动 | 0 |
| 目录体积 | 62 MB |
| 占用进程 | 无 |
| 目标位置 | 不存在（无覆盖风险） |

## 2. 执行结果

```text
<workspace-root>/
├── llmke/                        # git 仓 A（未移动）
├── doc2md/                       # git 仓 B（由 <旧位置>/doc2md 平级迁入）
├── llmke-doc2md.code-workspace   # 多根工作区（不入任何仓）
└── coordination/                 # 跨仓共享区（无 .git）
    ├── BOUNDARY.yaml             # 五条仓边界约束（B-1…B-5）
    ├── doc2md.lock               # 冻结 commit + 四个版本号 + 五个文件 md5
    ├── README.md
    ├── samples/                  # 6 份探针样本（3 PDF + 3 DOCX）
    └── probe/routing.json        # 契约探测结果
```

## 3. 迁移后验证（逐项通过）

| 检查 | 结果 |
|---|---|
| git 仓完整性 | `git rev-parse --show-toplevel` = 新位置；HEAD 仍 `d9e4f98`；未提交改动 0 |
| 原位置 | 已不存在（无残留） |
| 014 基线测试 | `pytest tests/test_pdf_sniffing.py tests/test_parser_router_v2.py -q` → **61 passed**（与迁移前一致，未退化） |
| 冻结文件指纹 | 5 个文件 md5 与迁移前逐字一致（`pdf_sniffing.py`/`parser_routing.py`/`mineru_pdf_parser.py`/`cli/main.py`/`config/pdf_sniffing.yaml`） |
| 相对路径解析 | `StorageConfig` 的 7 个 root 全部落在 `<workspace-root>/doc2md/` 下 |
| `PROJECT_ROOT` | 由 `__file__.parents[3]` 推导，随迁移自动正确 |

## 4. 遗留（doc2md 侧，按"只读"边界不由 LLMKE 修改）

| 项 | 数量 | 说明 |
|---|---|---|
| 文档仍引用旧绝对路径 | 13 个 `.md` | 主要是 `docs/role_prompts/*.md`、handoff 记录；agent 按旧路径会找错目录，建议 doc2md 维护方批量替换 |
| 运行时产物含旧绝对路径 | 22 个 `.json` | `raw_vault/*/file_metadata.json` 等历史记录；保留即可，重新解析会写新路径 |
| 代码注释含旧路径 | 1 个 `.py` | `docs/demo/.../make_demo_pdf.py` 的 docstring |
| 明文口令 | 1 处 | `config/app.yaml`（既有问题）；处置建议见决议 §5，需 doc2md 维护方执行并轮换 |

## 5. 未做的事

- 未修改 doc2md 任何文件（含上述 36 个含旧路径的文件）；
- 未启用 submodule、未合并 CI、未共享解释器；
- 未把 `coordination/` 纳入任何 git 仓。
