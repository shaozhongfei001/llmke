# R14 Loop3：隔离目录 + 独立库首次实装演练报告

执行：E-deliver　日期：2026-10-27 13:21 起　执行器：`platform/r12/bin/rehearsal.sh`
原始数据：`platform/r12/logs/rehearsal-20261027T132155Z.tsv`（逐 step：start / end / duration_ms / result / detail）

## 0. 环境身份（必须先看，不许含糊）

| 项 | 事实 |
|---|---|
| 宿主 | **共享宿主**（本机），**不是干净目标机**、不是独立 VM |
| 安装前缀 | `/home/szf/data/r14-rehearsal`（**偏离计划的 `/opt/r12-r14-rehearsal`**：本机 `sudo` 需密码，`/opt` 不可写） |
| 数据库 | 同一 `r12-mysql` 容器内的**独立 schema `gienrag_r14`**（现网 `gienrag` 未动，两者各 41 张表） |
| Nacos | 同一 Nacos 的**独立命名空间 `r14-rehearsal`**（public 与演练各 9 条配置，互不覆盖） |
| 基础设施容器 | **共用现网那一套**（MySQL/Redis/MinIO/ES/Nacos/Nebula/Milvus/RocketMQ）——这是共享宿主演练的固有局限 |
| 运行时资产来源 | 离线包 `platform/r12/dist/offline`（24G：images.tar 6.3G + payload 17.7G），**拷贝**到独立前缀，不软链、不指向仓库 |
| 业务实例 | **未启动**（模型需再占 ~15G 显存；Java 端口需重映射）→ 见 §5 未验证项 |
| 现网影响 | `gienrag` 41 表、`public` 9 条配置、`up.sh verify exit=0`、8088/18088 均未变 |

## 1. 逐步耗时与结果

| # | 步骤 | 耗时 | 结果 |
|---|---|---|---|
| 1 | preflight（磁盘 702G 可用 / 包 18G / 端口 28088、28081-28085 空闲） | 370 ms | pass |
| 2 | `sha256sum -c SHA256SUMS` | — | **FAIL（见 §2-F1，交付阻断）** |
| 3 | payload → 独立前缀（tar 管道，18G） | **41.6 s** | pass |
| 4 | 覆盖为仓库当前 `bin/ systemd/ .env.template`（偏差，见 §3） | 21 ms | pass |
| 5 | `install-paths.sh --dry-run → apply → --check` | 1.4 s / 0.34 s | pass（无构建机路径残留；动作 11–20 条，二次运行幂等） |
| 6 | 环境变量 `cp .env.template → .env` + 按 conf 占位符补齐 | 14 ms | pass（见 §2-F4） |
| 7 | `init-db`（独立 schema `gienrag_r14`） | 6.9 s 首次 / 0.46 s 幂等 | pass（41 张表；默认助手不变量；接口注册表 443+1 行） |
| 8 | `init-nacos --namespace r14-rehearsal`（长度+sha256 回读） | 216 ms | pass（9/9） |
| 9 | `es-single-node.sh`（幂等，共享 ES 必须 no-op） | 65 ms | pass（green / unassigned=0） |
| 10 | `check-units` + conf 占位符 vs `.env` | 54 ms | pass（修 §2-F4 后） |
| 11 | 业务实例启动 | — | **skip（未验证项）** |

## 2. 失败点与修复（本次演练的主要产出）

### F1【交付阻断】离线包 `SHA256SUMS` 已过期 → 客户第 2 步就会失败
```
$ sha256sum -c SHA256SUMS
payload/db/gienrag.sql: 失败
$ grep gienrag.sql SHA256SUMS   -> 4125543d…（期望）
$ sha256sum payload/db/gienrag.sql -> 2570362787…（实际）
文件 mtime 2026-10-27 12:00:41；SHA256SUMS mtime 2026-10-27 00:52:29
```
原因：12:00 有人重导/替换了 `payload/db/gienrag.sql`（含 C 的 `uk_search_config_default` 补丁），但**清单没有重算**。
影响：安装文档第 2 步禁用 `--ignore-missing`，客户会在这里直接停住；或有人为绕过而忽略校验 → 后面的问题都变成"环境玄学"。
处置：**必须在候选冻结后的重打中重算 SHA256SUMS**（`offline-kit.sh pack` 会自动重算）。

### F2【交付阻断】包内 `INSTALL-OFFLINE.md` 仍是 R13 顺序
```
包内（12:00 生成）：5) 初始化数据库与 Nacos 配置 → 6) 起容器（基础设施）   ← init-db 要求容器先起
仓库当前生成版：   5) 起基础设施并等就绪 → 6) init-db → 7) Nacos+回读 → 7.1 端点注册 → 8) ES 治理 …
```
影响：照包内文档装会在第 5 步失败（正是 F07 指出的顺序倒置）。
处置：已加 `offline-kit.sh doc` 子命令，可在不打包的情况下生成最新文档（本次演练即用它）；重打时自动带新文档。

### F3【交付阻断】包内 `bin/ systemd/ .env.template` 缺今天的全部修复
缺：`init-endpoints.sh`、`check-units.sh`、`gates-selftest.sh`、`boot-timing.sh`、`es-single-node.sh` 的调用点、
`up.sh verify` 的占位符 must 与 STALE warn 段、`r12-watchdog` 三处缺陷修复、`.env.template` 的 `R12_MYSQL_PASSWORD`。
处置：见 §3 偏差（演练用仓库当前脚本覆盖）；**重打是唯一正解**。

### F4【安装器缺陷，已修】`init-db` 把"接口注册表补齐"放在建库之前
```
== 接口注册表补齐 ==  [FAIL] 查询 interface_info 失败: ERROR 1049 Unknown database 'gienrag_r14'
```
原因：我为了让"升级已有库"也补注册，把调用点前移到建库/导入之前——全新库必然失败。
修复：改为**两条路径都在表就绪之后**执行：
- 已有业务表 → 跳过导入 → 不变量校验 → **接口注册表补齐** → exit 0；
- 全新库 → 建库 → 导入 → 表数校验 → 不变量校验 → **接口注册表补齐** → 行数抽样。
复测：全新 schema `gienrag_r14` 一次通过（41 表），二次运行幂等。

### F5【安装器缺陷，已修】`init-nacos` 两个问题
1. **回读瞬时 404**：发布 9 条后立即回读，9 条全部 `HTTP Error 404`；1 秒后用同样参数 curl 全部 200。已加**重试 4 次（退避 1/2/3s）**，并把判据从"只比长度"升级为**长度 + sha256 摘要**（长度相同但内容被改写必须失败）。
2. **路径检查误报**：`/…/logs/parse/layout_garbage` 被判"目标机不存在"——它是运行期才创建的产物。已把 `/logs/` 下路径排除。
复测：`[ok] Nacos 配置发布并回读校验（长度+sha256）9/9 namespace=r14-rehearsal`。

## 3. 偏差声明（不掩盖）

| 偏差 | 原因 | 对结论的影响 |
|---|---|---|
| 前缀为 `/home/szf/data/r14-rehearsal` 而非 `/opt/...` | 本机无 root（`sudo -n` 需密码） | 不改变"独立目录"实质，但没有验证"/opt 权限/属主"这条路径 |
| 用仓库当前 `bin/ systemd/ .env.template` 覆盖包内旧版 | 包内脚本早于今天所有安装器修复 | 验证的是**修好后的安装器**；同时证明"现包不能用"（F2/F3） |
| 未启动业务实例 | 模型需再占 ~15G 显存；Java 端口需重映射 + 对应命名空间配置改端口 | **未验证**：5 个服务冷启动、端口映射、模型加载、前后端联通 |
| 基础设施共用现网容器 | 单机资源与端口限制 | 未验证：独立 compose 全栈起停、数据面隔离 |
| 包内 jar/venv/模型为拷贝 | 离线包已含资产 | 未验证：目标机首次获取/构建依赖 |

## 4. 端口对照（计划 vs 实际）

| 用途 | 现网（未改） | 演练计划 | 实际 |
|---|---|---|---|
| 网关 | 8088 | 28088 | 未启动 |
| 业务 | 18081–18085 | 28081–28085 | 未启动 |
| 算法 | 19526/19527/19995/19996 | 28926/28927/28995/28996 | 未启动 |
| ES/MinIO/MySQL/Nacos | 19200/19000/13306/18848 | 共用（独立 schema/namespace） | 共用 |

## 5. 离"真正干净实装"还差什么（诚实清单）

1. **独立主机/VM**：本次是共享宿主；干净实装必须在独立机（或至少独立 docker daemon + 独立数据卷）验证"无宿主缓存依赖"。
2. **重打离线包并重算校验**：F1/F2/F3 三项都是"包与代码不同步"，只能靠重打解决；重打后必须再跑一次 `sha256sum -c` 与本次演练。
3. **业务实例冷启动**：需要 GPU 余量或独立主机；用 `bin/boot-timing.sh --restart` 采集"启动耗时 + 首探针就绪"，并验证端口重映射方案（`--server.port` / 命名空间配置改端口）。
4. **模型与 GPU**：目标机显卡/驱动/显存、模型许可、`n-gpu-layers` 适配；本次完全未验证。
5. **域名 + TLS + 入口**：8088/18088 目前是明文直连；生产需要反向代理、证书、HSTS、限流。
6. **运维账号与凭据交接**：独立口令、首登强制改密、密钥轮换、日志脱敏验证。
7. **备份/恢复/升级回退演练**：本次未做（属 Loop3 后半）。
8. **独立数据面**：本次共用 ES/MinIO/Milvus/Nebula；干净实装要验证"四类存储独立部署 + 索引重建"。
9. **systemd 托管与自愈**：演练前缀里已带 `systemd/`（含 watchdog），但未在独立机上 enable/验证开机自启与自愈。
10. **容量与余量**：本次只做了磁盘余量检查（702G 可用），未做镜像导入、双代索引、备份空间的完整测算。

## 6. 现场清理说明

- 演练前缀 `/home/szf/data/r14-rehearsal`（18G）**暂时保留**作为证据；确认后可用 `rm -rf` 清除。
- 独立库 `gienrag_r14`（41 表）与 Nacos 命名空间 `r14-rehearsal`（9 条配置）保留；如需清理：
  ```sql
  drop database gienrag_r14;
  ```
  ```bash
  curl -X DELETE 'http://127.0.0.1:18848/nacos/v1/console/namespaces?namespaceId=r14-rehearsal'
  ```
- **现网未受影响**：`gienrag` 41 表、`public` 9 条配置、`up.sh verify exit=0`、19529 pid 未变。
