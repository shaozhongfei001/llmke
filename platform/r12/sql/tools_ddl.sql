CREATE TABLE IF NOT EXISTS tools_database (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  name VARCHAR(128) COMMENT '数据库名称',
  description VARCHAR(512) COMMENT '描述',
  datasource_type VARCHAR(32) COMMENT '数据源类型 DataTable/DirectDB',
  db_type VARCHAR(32) COMMENT '数据库类型',
  db_host VARCHAR(128) COMMENT '主机',
  db_port INT COMMENT '端口',
  db_database VARCHAR(128) COMMENT '库名',
  db_user VARCHAR(128) COMMENT '账号',
  db_password VARCHAR(512) COMMENT '密码(密文)',
  jdbc_url VARCHAR(512) COMMENT 'JDBC URL',
  jdbc_driver_class VARCHAR(255) COMMENT '驱动类',
  gmt_create DATETIME DEFAULT CURRENT_TIMESTAMP,
  gmt_modified DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  create_by VARCHAR(64),
  update_by VARCHAR(64),
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='结构化查询-数据库配置';

CREATE TABLE IF NOT EXISTS tools_table (
  id BIGINT NOT NULL AUTO_INCREMENT,
  database_id BIGINT COMMENT '所属数据库',
  business_name VARCHAR(255) COMMENT '业务名',
  physical_name VARCHAR(255) COMMENT '物理表名',
  description TEXT COMMENT '表描述',
  column_count INT DEFAULT 0,
  row_count BIGINT DEFAULT 0,
  gmt_create DATETIME DEFAULT CURRENT_TIMESTAMP,
  gmt_modified DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  create_by VARCHAR(64),
  update_by VARCHAR(64),
  is_gen_desc TINYINT(1) DEFAULT 0,
  gen_desc_err_msg VARCHAR(1024),
  gen_desc_status VARCHAR(32),
  PRIMARY KEY (id),
  KEY idx_db (database_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='结构化查询-表元数据';

CREATE TABLE IF NOT EXISTS tools_table_column (
  id BIGINT NOT NULL AUTO_INCREMENT,
  database_id BIGINT,
  table_id BIGINT,
  business_name VARCHAR(255),
  physical_name VARCHAR(255),
  description VARCHAR(1024),
  data_type VARCHAR(128),
  gmt_create DATETIME DEFAULT CURRENT_TIMESTAMP,
  gmt_modified DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  create_by VARCHAR(64),
  update_by VARCHAR(64),
  PRIMARY KEY (id),
  KEY idx_tbl (table_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='结构化查询-字段元数据';

CREATE TABLE IF NOT EXISTS tools_table_file (
  id BIGINT NOT NULL AUTO_INCREMENT,
  database_id BIGINT,
  table_id BIGINT,
  original_filename VARCHAR(255),
  folder_path VARCHAR(512),
  file_name VARCHAR(255),
  object_name VARCHAR(512),
  file_path VARCHAR(512),
  file_size DOUBLE,
  column_count INT DEFAULT 0,
  row_count BIGINT DEFAULT 0,
  status VARCHAR(32),
  use_time BIGINT,
  error_msg VARCHAR(1024),
  gmt_create DATETIME DEFAULT CURRENT_TIMESTAMP,
  gmt_modified DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  create_by VARCHAR(64),
  update_by VARCHAR(64),
  PRIMARY KEY (id),
  KEY idx_db (database_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='结构化查询-上传文件';
