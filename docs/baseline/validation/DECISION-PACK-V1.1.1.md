# 待批决策包（D-01 P-02 / D-02 requirements.lock）

- 生成：第三轮（B 策略），在 r5 冻结**之前**提出，避免先改后批
- 原则：两项都属「语义/依赖基线变更」，TL **不得**自行实施；未获批则保持现状并继续其它任务
- 本文件不参与源码快照与冻结控制面

---

## D-01 P-02：QA 签名的「接受时点」与「事后复核」分离

### 现状（实测）

| 事实 | 证据 |
|---|---|
| `qa_payload.py` 生成的载荷固定有效期为 **1 小时** | `scripts/qa_payload.py` |
| `verify_envelope()` 每次校验都检查 `issued <= now < expires` | `scripts/baseline_support.py:70-74` |
| 因此已 `accept-qa` 通过的 QA 证据，**1 小时后 `evidence-check` 必然失败** | 实测：`FAIL: invalid approval validity window` |
| `LD-legacy-discovery-r2` 的签名已过复核窗口 | 状态 DONE，但复查时不再通过 |

### 风险

1. **长期不可复核**：任何一次合入后的例行复验，都会因签名过期而报错，逼着人「重签」——重签本身会掩盖「当时到底是谁签的」。
2. **诱发绕过**：为让门禁变绿，压力会转向「放宽有效期」或「跳过复核」，两种都比现状危险。
3. **历史证据语义漂移**：不区分「当时接受过」与「现在仍然有效」，两份结论会被混用。

### 需要的决定（qa-owner）

三选一，请明确选一项并写明判定口径：

| 选项 | 口径 | 影响 |
|---|---|---|
| **A（TL 建议）** | **接受时**严格校验有效期；**复核时**只校验签名、subject 一致、密钥未撤销，不再校验 `expires_at`；记录新增 `accepted_at` / `accepted_by`；信任根新增 `revoked_key_ids` | 历史记录缺 `accepted_at`，需一次性回填或标记 `legacy` |
| B | 维持现状（复核也校验有效期），接受「每次复核需重签」 | 不改进；复核成本持续存在 |
| C | 延长有效期（如 30 天） | 治标；仍会在某天失效，且扩大签名可重放窗口 |

### 拟议实施方案（若选 A）

1. `verify_envelope(..., phase='accept'|'review')`：`review` 跳过 `expires_at`，其余不变；
2. `accept_qa` 写 `accepted_at`/`accepted_by` 到记录；
3. `evidence-check` 对 QA 记录走 `phase='review'`；无 `accepted_at` 的旧记录标 `attestation_scheme: legacy` 并沿用旧语义；
4. 信任根 `revoked_key_ids`：命中即复核失败（这是唯一应让历史证据失效的条件）。

### 验收（正反例必须都跑）

- 正例：载荷过期 2 小时后 `evidence-check` → **PASS**；同一载荷在 `accept-qa` → **FAIL**；
- 反例：把该 `key_id` 加入 `revoked_key_ids` → 复核 **FAIL**；
- 反例：篡改 `subject_sha256` → 复核 **FAIL**。

### 责任方与阻塞面

`qa-owner`。阻塞：所有「合入后仍需复核」的 QA 证据；当前不阻塞 r5 的建立与开发门禁。

---

## D-02 `requirements.lock` 去重与收敛

### 现状（实测）

| 指标 | 值 |
|---|---|
| 行数 | 105 |
| 唯一包 | 95 |
| **版本冲突的重复包** | **2**：`pip` = 25.0.1 / 26.2.1，`idna` = 3.19 / 3.20 |
| 与框架无关的重型包 | **14**：`cadquery`、`cadquery-ocp`、`casadi`、`nlopt`、`matplotlib`、`scikit-learn`、`trame`（及 `trame-*` 系列） |
| 直接后果 | `uv pip install -r requirements.lock` / `pip install -r requirements.lock` **无法解析**（同一包两个版本） |
| 当前变通 | 按脚本真实导入装最小依赖集，装在 `.venv`（Python 3.12.13）；**该依赖集未写入任何冻结文件** |

### 风险

1. **不可复现**：「按需装」的结果依赖执行者当天的判断，换台机器可能装出不同版本。
2. **`framework-verify` 的绿色依赖非受控环境**：127/145 passed 是在「我自选的最小依赖集」上取得的，不是锁定文件保证的。
3. **重型包混入**：把 `cadquery`/`vtk` 这类几何与可视化栈当作框架依赖，会让任何干净环境安装超时或失败。

### 需要的决定（baseline-owner）

| 选项 | 口径 | 代价 |
|---|---|---|
| **A（TL 建议）** | 拆两份：`requirements.lock` 只保留框架运行/测试真实需要的包并去重；重型与业务无关包移出（如需保留，另建 `requirements-optional.txt` 并注明用途） | 属依赖基线变更，须重冻结与重跑 |
| B | 只修 2 处版本冲突，其余不动 | 安装仍会拉入 14 个重型包 |
| C | 维持现状，仅在文档中说明「锁文件不可用」 | 复现性问题长期存在 |

### 拟议差异（草案，**未生效**）

基于 `scripts/**`、`tests/**` 的真实导入统计，框架需要的最小集合为：
`jsonschema`、`jsonschema-path`、`jsonschema-specifications`、`referencing`、`rpds-py`、
`openapi-spec-validator`、`openapi-schema-validator`、`requests`、`PyYAML`、
`pytest`、`pluggy`、`iniconfig`、`packaging`、`typing_extensions`、
`attrs`、`rfc3339-validator`、`lazy-object-proxy`。

> 该清单是**提议**，不是冻结事实。批准后需在干净容器里实测 `pip install -r` 成功 + `framework-verify` 全绿，才可写入锁文件。

### 验收（批准后执行）

1. 干净 venv（Python 3.12）`pip install -r requirements.lock` → 退出码 0；
2. `make framework-verify` → 退出码 0；
3. 记录安装后的 `pip freeze` 指纹，与锁文件逐包比对无差异；
4. 若保留 `requirements-optional.txt`，验证「不装它也能过框架门禁」。

### 责任方与阻塞面

`baseline-owner`。阻塞：真正的环境可复现性声明；**不阻塞** r5 的建立，但意味着 r5 的门禁结果仍须注明「依赖环境为已装最小集」。

---

## 两项的共同声明

- 本文件是**决策请求**，不是批准记录；在获批之前，仓库中不存在对应的代码/依赖变更。
- 任何一项获批后实施，都会改变控制面或依赖基线 → 需**再次**一次性冻结并重跑门禁；
  因此建议与下一次批次建立**合并到同一窗口**，不要单独触发重冻结。
