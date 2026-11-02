# V2 后续任务：环境位置与变量名

只写位置与变量名，不写任何真实口令。

- MySQL 隔离库：`127.0.0.1:13306`，库 `gienrag_v2_restore`；口令见 `~/data/dev/llmke-r12/platform/r12/.env` 的 `R12_MYSQL_ROOT_PASSWORD`。
- 模型服务地址：chat `127.0.0.1:18092`（qwen2.5-7b-instruct）、embedding `127.0.0.1:18090`（bge-m3）、VL `127.0.0.1:18093`。
- 回答模型密钥变量：`DSEEK_2026_SZF_KEY`（值在 `~/.bashrc`，非交互 shell 需显式加载）。
- DashScope 密钥变量：`DASHSCOPE_API_KEY`（值在 `~/.bashrc`）。
- Python 环境：工具 venv `/home/szf/data/dev/llmke-v2-toolenv/bin/python`；图引擎 venv `/home/szf/data/dev/hipporag-toolenv/bin/python`。
- 交付目录：`/home/szf/data/dev/delivery`。
- Q 验收命令入口：`python scripts/v2_q_acceptance.py --help`；全量命令见 `docs/NEXT.md` 的 8a 段。
