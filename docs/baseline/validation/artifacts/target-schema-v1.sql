-- LLMKE 目标 schema V1（由 schema-generate.py 生成；旧模型仅作参考）
-- 规范见 SCHEMA-STANDARD-V1.md；未含二级索引（无查询基线时不臆造）

CREATE TABLE `answer` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '修改时间（原 gmt_modified）',
  `dialogue_id` BIGINT NULL COMMENT '对话id',
  `question_id` BIGINT NULL COMMENT '问题id',
  `content` TEXT NULL COMMENT '答案内容',
  `type` VARCHAR(32) NULL DEFAULT '1' COMMENT 'TEXT：文本；VOICE：语音',
  `reference` MEDIUMBLOB NULL COMMENT '参考内容(json)',
  `database_reference` TEXT NULL COMMENT '数据库召回',
  `log_result` TEXT NULL COMMENT '算法评测日志(json)',
  `retrieve_recall_Param` TEXT NULL COMMENT '知识检索召回测试的参数',
  `recommend_question` TEXT NULL COMMENT '问题推荐',
  `llm_type` INT NULL DEFAULT 1 COMMENT '推理类型 1:推理接口, 2:表格推理接口 默认值1',
  `result_type` INT NULL,
  `resp_time` BIGINT NULL COMMENT '问答接口响应时间(毫秒)',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `api_key_info` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `api_key` VARCHAR(512) NOT NULL COMMENT 'apikey全局唯一',
  `target_id` INT NULL COMMENT '目标id',
  `status` INT NULL DEFAULT 1 COMMENT '状态 0:禁用；1:正常 默认值1',
  `biz_type` TINYINT NOT NULL DEFAULT 1 COMMENT '业务类型 1:助手配置',
  `expire_time` DATETIME(3) NOT NULL COMMENT '过期时间',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否删除 -1 删除  1 正常 默认值1（原 is_del）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '修改人（原 modify_by）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '修改时间（原 gmt_modified）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `biz_label` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT 'id',
  `target_id` BIGINT NOT NULL COMMENT '资源id',
  `label` VARCHAR(256) NOT NULL COMMENT 'label',
  `biz_type` TINYINT NOT NULL,
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '更新人（原 update_by）',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否删除 -1 删除  1 正常 默认值1（原 is_del）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `department_info` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` VARCHAR(255) NOT NULL COMMENT '部门名称',
  `code` VARCHAR(255) NULL COMMENT '部门编码',
  `admin` VARCHAR(255) NULL COMMENT '部门管理员',
  `parent_id` BIGINT NULL COMMENT '上级部门ID',
  `status` TINYINT NULL DEFAULT 1 COMMENT '状态：0:待激活；1:正常（已激活）；-1:删除',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '修改时间（原 gmt_modified）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '修改人（原 modify_by）',
  `seq` INT NULL COMMENT '顺序',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `dept_privilege` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT 'id',
  `target_id` BIGINT NOT NULL COMMENT '目标id',
  `dept_id` BIGINT NULL COMMENT '部门id',
  `biz_type` INT NULL,
  `permission` INT NOT NULL COMMENT '0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否删除 -1 删除  1 正常 默认值1（原 is_del）',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `dialogue` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `label` VARCHAR(255) NULL COMMENT '对话名称',
  `session_id` VARCHAR(128) NULL COMMENT '对话id',
  `status` INT NULL,
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '更新人（原 update_by）',
  `sys_type` INT NULL COMMENT '系统类型：0.智能会话，1.知识索引,3 临时会话',
  `config` TEXT NULL COMMENT '配置信息',
  `config_id` BIGINT NULL COMMENT '检索配置id',
  `config_history` TEXT NULL COMMENT '检索配置历史信息',
  `kb_id` BIGINT NULL COMMENT '知识库id',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `feedback` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `answer_id` BIGINT NULL COMMENT '答案id',
  `restult` INT NULL COMMENT '0：踩；1：赞',
  `user_name` VARCHAR(64) NULL COMMENT '用户登录名',
  `user_realname` VARCHAR(64) NULL COMMENT '用户真实名称',
  `dept_name` VARCHAR(30) NULL COMMENT '部门名称',
  `user_phone` VARCHAR(20) NULL COMMENT '手机',
  `que_error` VARCHAR(255) NULL COMMENT '理解问题有误',
  `ans_poor` VARCHAR(255) NULL COMMENT '回答不佳',
  `format_error` VARCHAR(255) NULL COMMENT '格式问题',
  `harmful_info` VARCHAR(255) NULL COMMENT '有害信息',
  `othres` VARCHAR(255) NULL COMMENT '其他',
  `supplement_explain` TEXT NULL COMMENT '补充说明',
  `ideal_answer` TEXT NULL COMMENT '理想回答',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '更新人（原 update_by）',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否删除 -1 删除  1 正常 默认值1（原 is_del）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `file_parse_task` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `kb_id` BIGINT NOT NULL COMMENT '知识库id',
  `kb_name` VARCHAR(256) NULL COMMENT '知识库名称',
  `file_id` BIGINT NOT NULL COMMENT '文件id',
  `file_name` VARCHAR(256) NULL COMMENT '文件库名称',
  `task_info` TEXT NULL COMMENT '任务详情',
  `status` INT NULL DEFAULT 1 COMMENT '状态 -1:删除 1:待处理 2:处理中,3:重试中 4: 成功 5: 处理失败',
  `start_time` TIMESTAMP NULL COMMENT '解析开始时间',
  `end_time` TIMESTAMP NULL COMMENT '解析结束时间',
  `retry_limit` INT NULL COMMENT '重试限制次数',
  `retry_times` INT NULL DEFAULT 0 COMMENT '已经重试次数',
  `error_msg` TEXT NULL COMMENT '失败原因',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '修改人（原 modify_by）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '修改时间（原 gmt_modified）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `folder_info` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` VARCHAR(512) NULL COMMENT '文件夹名称',
  `kb_id` BIGINT NULL COMMENT '知识库id',
  `type` INT NULL,
  `parent_id` BIGINT NULL COMMENT '父文件夹id',
  `folder_label` VARCHAR(512) NULL COMMENT '文件夹标签',
  `status` INT NULL DEFAULT 1 COMMENT '1：正常；-1：删除',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '更新人（原 update_by）',
  `full_path` VARCHAR(2000) NULL COMMENT '完整路径（包含结尾/)',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `group_info` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT 'id',
  `pid` BIGINT NULL DEFAULT 0 COMMENT '父id',
  `name` VARCHAR(50) NULL COMMENT '机构组名称',
  `description` VARCHAR(150) NULL COMMENT '描述',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否删除 -1 删除  1 正常 默认值1（原 is_del）',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `group_privilege` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT 'id',
  `target_id` BIGINT NOT NULL COMMENT '目标id',
  `group_id` BIGINT NULL COMMENT '机构组id',
  `biz_type` INT NULL,
  `permission` INT NOT NULL COMMENT '0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否删除 -1 删除  1 正常 默认值1（原 is_del）',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `interface_info` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `app_name` VARCHAR(128) NULL COMMENT '应用名称',
  `app_name_abbreviate` VARCHAR(128) NULL COMMENT '应用简称',
  `name` VARCHAR(128) NULL COMMENT '接口名称',
  `url` VARCHAR(128) NULL COMMENT 'url',
  `method` VARCHAR(16) NULL COMMENT '接口的请求方式',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `kb_label_his` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `kb_id` BIGINT NOT NULL COMMENT '知识库id',
  `labe` TEXT NULL COMMENT '知识库使用的标签',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否删除 -1 删除  1 正常 默认值1（原 is_del）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '修改人（原 modify_by）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '修改时间（原 gmt_modified）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `knowledge_base` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `kb_name` VARCHAR(128) NULL COMMENT '知识库名称',
  `primitive_name` VARCHAR(128) NULL COMMENT '知识库原始名称,对应算法知识库的名称',
  `kb_type` INT NULL DEFAULT 1 COMMENT '知识库类型 1:知识库 2: 文档上传问答',
  `kb_des` VARCHAR(255) NULL COMMENT '描述',
  `source_url` VARCHAR(128) NULL COMMENT '路径',
  `status` INT NULL,
  `config` TEXT NULL COMMENT '知识库解析配置',
  `kb_label` VARCHAR(128) NULL COMMENT '知识库标签',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '修改人（原 modify_by）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '修改时间（原 gmt_modified）',
  `platform` VARCHAR(128) NULL COMMENT '上层应用平台',
  `private_kb` INT NULL DEFAULT 0 COMMENT '是否私有知识库 0：非私有 1：私有',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `knowledge_base_list` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `kb_id` BIGINT NOT NULL COMMENT '知识库id',
  `file_id` VARCHAR(64) NULL COMMENT 'minIO文件的id',
  `file_name` VARCHAR(128) NULL COMMENT '文件id',
  `file_size` VARCHAR(255) NULL COMMENT '文件大小',
  `file_path` VARCHAR(256) NULL COMMENT '路径',
  `full_text_path` VARCHAR(256) NULL COMMENT '全文txt路径',
  `status` INT NULL DEFAULT 1 COMMENT '状态 0:删除 1:正常 2:解析中，3:解析成功 4: 解析失败',
  `is_enable` INT NULL,
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '修改人（原 modify_by）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '修改时间（原 gmt_modified）',
  `parsed_file_path` VARCHAR(255) NULL,
  `parse_type` INT NULL,
  `aq_count` INT NULL DEFAULT 0 COMMENT '问答对数',
  `faq_extract_status` INT NULL DEFAULT 1 COMMENT 'faq抽取状态 1 未抽取；2 抽取中 3 抽取成功 4 抽取失败',
  `graph_parse_status` INT NULL DEFAULT 1 COMMENT '图解析状态 1 未解析；2 解析中 3 解析成功 4 解析失败',
  `revise_date` VARCHAR(30) NULL COMMENT '修订实时间',
  `parent_file_name` VARCHAR(127) NULL COMMENT '父文件名称',
  `version` VARCHAR(16) NULL COMMENT '版本号',
  `converted_file_path` VARCHAR(512) NULL COMMENT '转化后的文件路径',
  `folder_id` BIGINT NULL COMMENT '文件夹id',
  `source_url` VARCHAR(1000) NULL COMMENT '文件url地址(从网页获取的文件)',
  `chunking` TINYINT NULL COMMENT '文件是否chunk化',
  `uid` VARCHAR(128) NULL COMMENT '文件的uid(uid是前端生成的,文档上传问答使用,通过uid来判断文件解析状态)',
  `temp_status` INT NULL DEFAULT 2 COMMENT '1 临时文件,2 持久化文件 默认值是2',
  `group_id` VARCHAR(512) NULL COMMENT '文件集群组id，算法端根据文件内容生成',
  `table_file_paths` LONGTEXT NULL COMMENT '表格解析后的文件路径',
  `pid` BIGINT NULL COMMENT '针对于FAQ管理，文件中有文件',
  `image_paths` TEXT NULL COMMENT '图片解析路径',
  `chunk_type` VARCHAR(32) NULL COMMENT '切片策略',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `model_info` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `model_name` VARCHAR(128) NULL COMMENT '模型名称',
  `type` TINYINT NULL DEFAULT 1 COMMENT '模型使用类型: 1:LLM大语言模型、2:Embedding嵌入、3:rerank排序、4:MultiModel图片解析',
  `model_protocol` TINYINT NULL COMMENT '模型传输协议,1-Baichuan、2-Qwen、3-GLM、4-openAI',
  `model_ide` VARCHAR(128) NULL COMMENT '待接入的模型ID',
  `api_key` VARCHAR(255) NULL COMMENT 'APIkey',
  `url` VARCHAR(255) NULL COMMENT '请求URL',
  `dec` VARCHAR(255) NULL COMMENT '说明',
  `status` TINYINT NULL COMMENT '状态,0-不可用,1-可用,3-检测中',
  `error_msg` VARCHAR(500) NULL COMMENT '报错信息',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '逻辑删除,0-未删除,1-已删除,默认为0（原 is_dtl）',
  `thinking` INT NULL DEFAULT 0 COMMENT '推理思考(qwen3相关模型的功能) 0:没有推理思考功能 1:有推理思考功能',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `question` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '修改时间（原 gmt_modified）',
  `dialogue_id` BIGINT NULL COMMENT '对话id',
  `content` TEXT NULL COMMENT '答案内容',
  `type` VARCHAR(32) NULL DEFAULT '1' COMMENT 'TEXT：文本；VOICE：语音',
  `front_uuid` VARCHAR(128) NULL COMMENT '前端生成的uuid',
  `alg_model` VARCHAR(128) NULL COMMENT '模型算法',
  `alg_params` TEXT NULL COMMENT '模型参数(json)',
  `knowledge_base_name` VARCHAR(128) NULL COMMENT '知识库名称',
  `knowledge_params` TEXT NULL COMMENT '知识库参数(json)',
  `audio_url` VARCHAR(512) NULL COMMENT '音频地址',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `re_embedding_file` (
  `id` BIGINT NOT NULL,
  `task_id` BIGINT NULL,
  `kb_id` BIGINT NULL,
  `kb_name` VARCHAR(255) NULL,
  `file_id` BIGINT NULL,
  `created_at` DATETIME(3) NOT NULL COMMENT '（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '（原 gmt_modified）',
  `total_chunk_num` BIGINT NULL,
  `processed_chunk_num` BIGINT NULL,
  `error_chunk_num` BIGINT NULL,
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '（原 is_del）',
  `is_migrate` INT NULL,
  `status` INT NULL,
  `last_error` VARCHAR(255) NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `re_embedding_retry_task` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `uid` VARCHAR(255) NULL,
  `task_id` BIGINT NULL,
  `type` INT NULL,
  `payload` VARCHAR(255) NULL,
  `last_error` VARCHAR(255) NULL,
  `created_at` DATETIME(3) NOT NULL COMMENT '（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '（原 gmt_modified）',
  `retry_times` INT NULL,
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '（原 is_del）',
  `status` INT NULL,
  `file_id` BIGINT NULL,
  `kb_id` BIGINT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `re_embedding_task` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `kb_id` BIGINT NULL,
  `kb_name` VARCHAR(255) NULL,
  `embedding_model_name` VARCHAR(255) NULL,
  `status` INT NULL,
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '（原 is_del）',
  `log_summary` VARCHAR(255) NULL,
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `msg_key` VARCHAR(255) NULL,
  `total_file_num` BIGINT NULL,
  `uid` VARCHAR(255) NULL,
  `created_by` VARCHAR(64) NOT NULL COMMENT '（原 create_by）',
  `modified_by` VARCHAR(255) NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `resource_info` (
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '逻辑删除 是否删除 1是 0否（原 is_dtl）',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '修改时间（原 gmt_modified）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '更新人（原 update_by）',
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` VARCHAR(128) NULL COMMENT '名称',
  `url` VARCHAR(2048) NULL COMMENT '路径',
  `description` VARCHAR(128) NULL COMMENT '描述',
  `icon` VARCHAR(200) NULL COMMENT '图标',
  `pid` BIGINT NULL COMMENT '父类id',
  `seq` BIGINT NULL COMMENT '排序',
  `status` VARCHAR(255) NULL DEFAULT '1' COMMENT '状态 0 禁用 1 启用',
  `resource_type` VARCHAR(255) NULL,
  `code` VARCHAR(64) NULL COMMENT '编码',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `resource_interface` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `resource_id` BIGINT NULL COMMENT '权限id',
  `interface_id` BIGINT NULL COMMENT '接口id',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否删除 -1 删除  1 正常 默认值1（原 is_del）',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `role_info` (
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '逻辑删除 是否删除 1是 0否（原 is_dtl）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '更新人（原 update_by）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` VARCHAR(128) NULL COMMENT '角色名称',
  `description` VARCHAR(512) NULL COMMENT '描述',
  `seq` BIGINT NULL COMMENT '排序',
  `status` INT NULL DEFAULT 1 COMMENT '状态 0 禁用 1 启用',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `role_resource` (
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '逻辑删除 是否删除 1是 0否（原 is_dtl）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '更新人（原 update_by）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `role_id` BIGINT NULL COMMENT '角色id',
  `resource_id` BIGINT NULL COMMENT '资源id',
  `status` INT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `search_config` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `status` INT NULL DEFAULT 1 COMMENT '状态 0:禁用；1:正常 默认值1',
  `is_default` INT NULL DEFAULT 1 COMMENT '是否默认 0:否；1:是 默认值1',
  `config_json` TEXT NULL COMMENT '配置详情',
  `name` VARCHAR(50) NULL COMMENT '名称',
  `des` VARCHAR(255) NULL COMMENT '描述',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '修改人（原 modify_by）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '修改时间（原 gmt_modified）',
  `sensitive_word_ids` VARCHAR(255) NULL COMMENT '敏感词id',
  `default_answer` VARCHAR(255) NULL COMMENT '默认回答(sensitive_word_ids不为空时,必填)',
  `enabled_faq` INT NULL DEFAULT 0,
  `depend_on_kb` INT NULL DEFAULT 0,
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否删除 -1 删除  1 正常 默认值1（原 is_del）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `sensitive_words` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '修改时间（原 gmt_modified）',
  `name` VARCHAR(512) NULL COMMENT '敏感词库名称',
  `descript` VARCHAR(512) NULL COMMENT '描述',
  `words` LONGTEXT NULL COMMENT '敏感词详情',
  `status` INT NULL COMMENT '状态，1正常，-1删除',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `syn_log` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `kb_id` BIGINT NULL COMMENT '知识库id',
  `target_id` BIGINT NULL COMMENT '目标id（知识库id）',
  `log_type` INT NULL,
  `error_code` VARCHAR(16) NULL COMMENT '异常码 (如果为-1的话，接口不可用)',
  `error_message` TEXT NULL COMMENT '异常信息',
  `error_detail` TEXT NULL COMMENT '异常信息详情',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `tools_database` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` VARCHAR(100) NULL COMMENT '数据库名称',
  `description` VARCHAR(500) NULL COMMENT '数据库描述',
  `datasource_type` VARCHAR(32) NULL COMMENT '数据源类型',
  `db_type` VARCHAR(32) NULL COMMENT '数据库类型',
  `db_host` VARCHAR(255) NULL COMMENT '连接地址',
  `db_port` INT NULL COMMENT '连接端口',
  `db_database` VARCHAR(100) NULL COMMENT '数据库名称',
  `db_user` VARCHAR(100) NULL COMMENT '连接用户',
  `db_password` VARCHAR(255) NULL COMMENT '连接密码',
  `jdbc_url` VARCHAR(500) NULL COMMENT 'jdbc连接地址',
  `jdbc_driver_class` VARCHAR(255) NULL COMMENT 'jdbc驱动类名',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `tools_table` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `database_id` BIGINT NULL COMMENT '数据库编号',
  `business_name` VARCHAR(100) NULL COMMENT '业务表名',
  `physical_name` VARCHAR(100) NULL COMMENT '物理表名',
  `description` VARCHAR(3000) NULL COMMENT '表描述',
  `column_count` INT NULL COMMENT '列数量',
  `row_count` BIGINT NULL COMMENT '行数量',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '更新人（原 update_by）',
  `is_gen_desc` TINYINT NULL COMMENT '更新人',
  `gen_desc_err_msg` VARCHAR(1024) NULL COMMENT '更新人',
  `gen_desc_status` VARCHAR(16) NULL COMMENT '更新人',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `tools_table_column` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `database_id` BIGINT NULL COMMENT '数据库编号',
  `table_id` BIGINT NULL COMMENT '数据表编号',
  `business_name` VARCHAR(100) NULL COMMENT '业务列名',
  `physical_name` VARCHAR(100) NULL COMMENT '物理列名',
  `description` VARCHAR(500) NULL COMMENT '列描述',
  `data_type` VARCHAR(50) NULL COMMENT '数据类型',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `tools_table_file` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `database_id` BIGINT NULL COMMENT '数据库编号',
  `table_id` BIGINT NULL COMMENT '数据表编号',
  `original_filename` VARCHAR(255) NULL COMMENT '原始文件名称',
  `folder_path` VARCHAR(255) NULL COMMENT '存储文件夹路径',
  `file_name` VARCHAR(255) NULL COMMENT '文件名称',
  `object_name` VARCHAR(255) NULL COMMENT '存储对象名称',
  `file_path` VARCHAR(255) NULL COMMENT '文件路径',
  `file_size` DOUBLE NULL COMMENT '文件大小',
  `column_count` INT NULL COMMENT '列数量',
  `row_count` BIGINT NULL COMMENT '行数量',
  `status` VARCHAR(255) NULL COMMENT '解析状态',
  `use_time` BIGINT NULL COMMENT '解析耗时(毫秒)',
  `error_msg` VARCHAR(1000) NULL COMMENT '错误信息',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `user_group` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT 'id',
  `user_id` BIGINT NULL COMMENT '用户id',
  `group_id` BIGINT NULL COMMENT '机构分组id',
  `dept_id` BIGINT NULL COMMENT '部门id',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否删除 -1 删除  1 正常 默认值1（原 is_del）',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `user_info` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_name` VARCHAR(128) NOT NULL COMMENT '用户名',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '更新人（原 update_by）',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '逻辑删除 是否删除 1是 0 未删除（原 is_dtl）',
  `user_password` VARCHAR(512) NOT NULL COMMENT '密码',
  `user_realname` VARCHAR(128) NULL COMMENT '真实姓名',
  `user_email` VARCHAR(128) NULL COMMENT '邮箱',
  `url` VARCHAR(255) NULL COMMENT '用户头像',
  `user_phone` VARCHAR(20) NULL COMMENT '手机',
  `status` INT NULL DEFAULT 1 COMMENT '状态  1启用 0禁用',
  `expire_time` DATETIME(3) NULL COMMENT '过期时间',
  `miss_num` INT NULL DEFAULT 0 COMMENT '密码错误次数',
  `password_updated` DATETIME(3) NULL COMMENT '密码更改时间',
  `admin_reset_password` VARCHAR(128) NULL COMMENT '管理员重置的密码',
  `ip` VARCHAR(50) NULL COMMENT 'ip',
  `online_time` DATETIME(3) NULL COMMENT '上线时间',
  `organization_id` BIGINT NULL COMMENT '机构id',
  `emp_no` VARCHAR(128) NULL COMMENT '用户工号',
  `dept_id` VARCHAR(30) NULL COMMENT '部门id',
  `dept_name` VARCHAR(30) NULL COMMENT '部门名称(冗余字段)',
  `app_key` VARCHAR(128) NULL COMMENT '认证key',
  `resign_date` DATETIME(3) NULL COMMENT '离职日期',
  `feature` VARCHAR(1000) NULL COMMENT '用户特征',
  `system_source` INT NULL COMMENT '用户来源',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `user_operate` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `gmt_created` DATETIME(3) NULL COMMENT '创建时间',
  `updated_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_modified）',
  `name` VARCHAR(255) NULL COMMENT '方法名称',
  `url` VARCHAR(255) NULL COMMENT '方法url',
  `start_time` DATETIME(3) NULL COMMENT '接口请求开始时间',
  `end_time` DATETIME(3) NULL COMMENT '接口请求结束时间',
  `user_id` BIGINT NULL COMMENT '用户id',
  `user_name` VARCHAR(128) NULL COMMENT '用户名称',
  `params` TEXT NULL COMMENT '参数',
  `ip` VARCHAR(20) NULL COMMENT 'ip',
  `success` INT NULL COMMENT '接口是否请求成功 0 否  1是 默认值1',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `user_privilege` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT 'id',
  `target_id` BIGINT NOT NULL COMMENT '配置id',
  `user_id` BIGINT NULL COMMENT '用户id,-1代表所有人',
  `biz_type` INT NULL,
  `permission` INT NOT NULL COMMENT '0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限',
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否删除 -1 删除  1 正常 默认值1（原 is_del）',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `user_role` (
  `is_deleted` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '逻辑删除 是否删除 1是 0 否（原 is_dtl）',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '更新人（原 update_by）',
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键',
  `role_id` BIGINT NOT NULL COMMENT '角色id',
  `user_id` BIGINT NOT NULL COMMENT '用户id',
  `status` INT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `user_security_question` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键编号',
  `user_id` BIGINT NULL COMMENT '用户编号',
  `question` VARCHAR(500) NULL COMMENT '问题',
  `answer` VARCHAR(500) NULL COMMENT '答案',
  `created_at` DATETIME(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` DATETIME(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` VARCHAR(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` VARCHAR(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
