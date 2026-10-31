# 常驻进程与启动顺序：把演练脚本变成能交给 systemd 的服务（2026-11-01）

之前调度器/租约/指标/告警都只在演练脚本里存在：跑完就退出、没人守护、没有端点。
这一轮把它们装成一个**长驻进程**，并补上 `ExecStartPre` 依赖探针。

## 1. `scripts/v2_graph_worker.py`：能长驻的那个进程

- 循环：`RebuildScheduler.run(stop_event)`，SIGTERM/SIGINT 在下一个检查点退出；
- 多实例：`--lease-backend file|mysql`，拿不到租约只跟随、不构建；
- 观测：`/healthz`（含 owner/fencing）与 `/metrics`（Prometheus 文本，标准库实现）；
- 告警：`--alert-webhook` 走 `WebhookAlertSink`（永不抛，失败只记账）。

实测（后台起、curl、kill -TERM）：

```
/healthz → {"status":"ok","owner":"x2:3096604","fencing":null}
/metrics → 66 行，含 llmke_graph_scheduler_cycles_total
kill -TERM 后 3s 内退出，日志 {"event":"stop","uptime_s":8.3,"cycles":8,...}
```

一个自己踩的坑：第一版启动时 `coord.request("worker-ready")`，等于**每次启动都触发一次重建**。
服务重启会连带跑一遍 LLM 抽取，这在运维上是灾难。已删掉，只保留显式 `--enqueue-on-start`。

## 2. `scripts/wait_ready.py`：依赖没起来就别启动

为什么需要：服务连不上 Nacos/MySQL 时会**启动即崩**，`Restart=always` 于是变成每 5 秒崩一次的
循环，日志被刷满、真因埋在栈里，`StartLimit` 还会把 unit 打成 failed。

三种探针：`tcp HOST PORT`、`http URL`、`nacos`（拉一次配置，比只看端口更接近真实依赖）。
退出码 0 就绪 / 2 超时。实测：

```
tcp 127.0.0.1 18848 → READY（第 1 次）
tcp 127.0.0.1 1     → TIMEOUT（4 次尝试，ConnectionRefusedError）
```

## 3. systemd 单元与渲染

`deploy/systemd/llmke-v2-graph-worker.service` + `.env.example`，用 `@REPO@` / `@PYTHON@`
占位；`scripts/install_systemd_units.py` 渲染后交 `systemd-analyze verify` 校验。

两个细节：
- **`systemd-analyze verify` 会扫整机所有 unit**，本机既有 `netplan`/`spark`/`serviceqaxsafe`
  的告警会一起冒出来。所以只认"与本单元名相关"的行，否则验证永远红；
- 它对"Executable not found"只警告、返回码仍为 0，必须自己看输出，不能只看 rc。

实测：渲染 1 个单元、`PASS`。

## 4. 还没做 / 边界

- **没有在真实 systemd 上 `enable/start`**：本机是容器内环境，只做了渲染 + `systemd-analyze`；
- **没有演练"依赖恢复后自动起来"**：探针超时会让 unit failed，需要 `systemctl reset-failed`
  或由 watchdog 触发，这条链路没测；
- worker 的 `--payloads` 是**静态文件**，真实部署需要有人持续写它（数据库/对象存储同步未做）；
- `/metrics` 没有鉴权，只监听 127.0.0.1（依赖部署侧网络隔离）；
- 只给 graph worker 写了 unit；parse 服务仍用 llmke-r12 里的旧单元，未统一。
