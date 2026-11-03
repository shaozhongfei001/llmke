-- 002_rebuild_lease：跨机重建选主用的租约表
--
-- 为什么要有这个文件：生产上 DDL 权限通常收紧，应用不应在启动时自动建表。
-- 这里把**与 lease_mysql.DDL 逐字一致**的语句放在版本库里，供 DBA 预建；
-- tests/test_lease_schema_migration.py 会断言两边不漂移（改了代码忘了改 SQL 会失败）。
--
-- 语义要点（改表前必须读）：
--   * fencing 在**接管时 +1**、自己续租不变；release 只把 expires_at 置 0 并**保留行**，
--     删行会让 fencing 从 1 重来，旧主的晚到写入就又能覆盖当前快照；
--   * expires_at/taken_at 是 unix 秒（DOUBLE），不用 DATETIME：避免时区与秒级精度问题。

CREATE TABLE IF NOT EXISTS v2_rebuild_lease (
  lease_key  VARCHAR(64)  NOT NULL,
  owner      VARCHAR(191) NOT NULL,
  fencing    BIGINT       NOT NULL DEFAULT 0,
  expires_at DOUBLE       NOT NULL DEFAULT 0,
  taken_at   DOUBLE       NOT NULL DEFAULT 0,
  PRIMARY KEY (lease_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
