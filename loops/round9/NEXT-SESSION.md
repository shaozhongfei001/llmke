# ROUND9 续跑说明

## 下一条命令
```bash
cd ~/data/dev/llmke
export PATH=$PWD/.venv/bin:$PATH
python -m pytest modules/answer_api/tests -q > /tmp/t9.log 2>&1; echo "rc=$?"; tail -5 /tmp/t9.log
```

## 顺序
1. `R9-T01` 已 VERIFIED；
2. `R9-T02` 纯逻辑 + 负例；`R9-T03` 真库端到端；
3. `R9-T04` 口径索引（可选，非阻塞）；
4. `R9-T05` 等 data-owner 真实 DDL，本轮最多 dry-run。
