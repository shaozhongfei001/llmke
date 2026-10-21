# 共享记忆与故障恢复

STATE.json 是唯一状态记录。ROLE_BOARD、NEXT_SESSION、ORCHESTRATOR 是带 state_revision 的派生视图。进程在视图渲染中死亡时，运行 `python3 scripts/loop_guard.py render-views --loop <id>`，不得把旧Markdown反写权威状态。

接力必须读当前revision，用CAS在锁内更新；错误revision、未知holder或非当前holder/TL拒绝。锁由操作系统在进程死亡时释放，不靠删除lock文件恢复。transfer不能清除业务BLOCKED。

记录分四类：事实（带版本/证据）、待确认推断（带推翻条件/实验）、批准决议（带authority/ref）、执行结果（带快照/hash/退出码）。B-10只是条件推断，不能变成“一开图就HTTP500”。

失败事件先落盘再写状态；途中死亡导致未完成的gate不可继承为PASS，已预扣的attempt保留。恢复先核对当前源码和证据新鲜度，不能修改sha使旧日志看似适用。
