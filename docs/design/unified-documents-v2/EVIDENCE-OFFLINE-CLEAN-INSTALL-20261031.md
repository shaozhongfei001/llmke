# 离线交付：干净目标安装验收（2026-10-31）

入口 `scripts/v2_verify_offline_bundles.py`，报告 `offline/clean-install-verify.json`。

做法：为每个 wheelhouse **新建空 venv**，只用 `pip --no-index --find-links` 装（不联网、
不借用现成 site-packages），再验关键导入。这是"干净目标机"的近似。

## 结果

```
{"PASS": 4, "FAIL": 0, "SKIP": 0}  verdict=PASS
```

| 组件 | 包数 | 用时 | 说明 |
|---|---|---|---|
| parse | 153 | 79.5 s | 需额外从 models 包补 `torch==2.6.0+cpu` |
| alg | 103 | 26.1 s | 自足 |
| models | 44 | 153.5 s | 含 torch 2.6.0+cpu |
| graph | 106 | 19.2 s | 自足 |

## 查出来的一处真实交付缺口

**parse/alg/graph 的 wheelhouse 里没有 torch**（按各自 requirements 收集，torch 只落在 models 包里）。
第一次跑 parse 就是 `ModuleNotFoundError: torch`。

这不是版本 bug，是**打包边界问题**：干净机上必须先装 models 包的 torch，parse 才能 import。
已在脚本里把它写成显式"跨包依赖"（`extra_used` 记进报告），不允许再出现"装完看着成功、
其实缺 torch"的假通过。

## 边界（不许当成已完成）

- 只验了 venv 层安装与导入，**没有**验服务启动、端口占用、配置文件、数据库连接；
- 镜像 tar（6 个 / 3.98G）只做了清单与校验，未在本轮做实际 `docker load` 到干净宿主机；
- 未做**差分升级**演练（旧版本 → 新版本覆盖装 + 回滚）；
- MinerU 的 wheelhouse 仍未打包（torch 构建选型未定，见 A2-MINERU-INTEGRATION.md §6）。
