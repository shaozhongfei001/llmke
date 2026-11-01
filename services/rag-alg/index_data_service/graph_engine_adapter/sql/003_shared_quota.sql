-- 003_shared_quota：跨实例共享配额用的计数窗口表
--
-- 为什么要有这个文件：生产上 DDL 权限通常收紧，应用不应在启动时自动建表。
-- 这里把**与 quota_shared.DDL 逐字一致**的语句放在版本库里，供 DBA 预建；
-- tests/test_quota_shared.py 会断言两边不漂移（改了代码忘了改 SQL 会失败）。
--
-- 语义要点（改表前必须读）：
--   * 主键 (tenant, window_start) 是全局唯一性的来源：多实例同时自增命中同一行，
--     靠 `INSERT ... ON DUPLICATE KEY UPDATE used = used + n` 在行锁下完成，
--     所以**没有主键就没有跨实例配额**（会退化成发现不了冲突的两次写）；
--   * window_start 是整数窗口号（floor(epoch / window_s)），不用 DATETIME：
--     避免时区、精度与"夏令时把两个窗口并成一个"的问题；
--   * used 是 INT，超过 21 亿次/窗口才溢出；溢出前应先在应用层把 limit 降下来；
--   * 清理只按 tenant + 时间下界删（见 quota_shared.SQL_PRUNE），
--     DBA 别写全表 DELETE 的定时任务，那会删掉别的租户正在用的窗口。

CREATE TABLE IF NOT EXISTS v2_quota_window (
  tenant       VARCHAR(128) NOT NULL,
  window_start BIGINT       NOT NULL,
  used         INT          NOT NULL DEFAULT 0,
  PRIMARY KEY (tenant, window_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
