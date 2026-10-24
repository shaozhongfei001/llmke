# ROUND10 中断恢复

## 下一条命令
```bash
cd ~/data/dev/llmke
export PATH=$PWD/.venv/bin:$PATH
~/data/dev/coordination/mysql-probe.sh start
python -m pytest tests/test_answer_server.py -q > /tmp/t.log 2>&1; echo "rc=$?"; tail -5 /tmp/t.log
```

## 顺序
1. T01 状态重建（已完成）；
2. T02 server + HTTP 语义测试（无 DB，fake runner）；
3. T03 真库端到端（seed → HTTP）；
4. T04 收口：一次冻结 + 建 r13 + 9 条门禁 + QA_PENDING。
