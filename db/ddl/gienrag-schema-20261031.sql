
/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `answer` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `gmt_modified` datetime DEFAULT NULL COMMENT '修改时间',
  `dialogue_id` bigint DEFAULT NULL COMMENT '对话id',
  `question_id` bigint DEFAULT NULL COMMENT '问题id',
  `content` text COLLATE utf8mb4_general_ci COMMENT '答案内容',
  `type` varchar(32) COLLATE utf8mb4_general_ci DEFAULT '1' COMMENT 'TEXT：文本；VOICE：语音',
  `reference` mediumblob COMMENT '参考内容(json)',
  `database_reference` text COLLATE utf8mb4_general_ci COMMENT '数据库召回',
  `log_result` text COLLATE utf8mb4_general_ci COMMENT '算法评测日志(json)',
  `retrieve_recall_param` text COLLATE utf8mb4_general_ci COMMENT '知识检索召回测试的参数',
  `recommend_question` text COLLATE utf8mb4_general_ci COMMENT '问题推荐',
  `llm_type` int DEFAULT '1' COMMENT '推理类型 1:推理接口, 2:表格推理接口 默认值1',
  `result_type` int DEFAULT NULL COMMENT '响应的类型 1:正常大模型推理; 2:FAQ; 3 命中敏感词;4 强知识依赖;5文档上传问答;6 表格问答',
  `resp_time` bigint DEFAULT NULL COMMENT '问答接口响应时间(毫秒)',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1111 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='答案表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `api_key_info` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `api_key` varchar(512) COLLATE utf8mb4_general_ci NOT NULL COMMENT 'apikey全局唯一',
  `target_id` int DEFAULT NULL COMMENT '目标id',
  `status` int DEFAULT '1' COMMENT '状态 0:禁用；1:正常 默认值1',
  `biz_type` tinyint NOT NULL DEFAULT '1' COMMENT '业务类型 1:助手配置',
  `expire_time` datetime NOT NULL COMMENT '过期时间',
  `is_del` int DEFAULT '1' COMMENT '是否删除 -1 删除  1 正常 默认值1',
  `create_by` varchar(30) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `modify_by` varchar(30) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '修改人',
  `gmt_modified` datetime DEFAULT NULL COMMENT '修改时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='apikey的信息';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `biz_label` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'id',
  `target_id` bigint NOT NULL COMMENT '资源id',
  `label` varchar(256) COLLATE utf8mb4_general_ci NOT NULL COMMENT 'label',
  `biz_type` tinyint NOT NULL COMMENT '1:知识库;2:检索配置;3:模型;4:文件',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `gmt_modified` datetime DEFAULT NULL COMMENT '更新时间',
  `create_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `update_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '更新人',
  `is_del` int DEFAULT '1' COMMENT '是否删除 -1 删除  1 正常 默认值1',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='用户-数据权限关联';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `consolidated_balance` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `file_id` bigint DEFAULT NULL,
  `file_name` varchar(512) DEFAULT NULL,
  `file_path` varchar(1024) DEFAULT NULL,
  `parsed_file_path` varchar(1024) DEFAULT NULL,
  `company_full_name` varchar(255) DEFAULT NULL,
  `company_short_name` varchar(255) DEFAULT NULL,
  `year` varchar(16) DEFAULT NULL,
  `period_type` varchar(32) DEFAULT NULL,
  `date_type` int DEFAULT NULL,
  `indicator_name` varchar(255) DEFAULT NULL,
  `indicator_raw` varchar(512) DEFAULT NULL,
  `indicator_value` varchar(255) DEFAULT NULL,
  `fixed_value` varchar(255) DEFAULT NULL,
  `indicator_unit` varchar(64) DEFAULT NULL,
  `indicator_value_position` text,
  `indicator_value_page_size` text,
  `indicator_value_offset` text,
  `indicator_value_page_number` text,
  `knowledge_base_name` varchar(255) DEFAULT NULL,
  `knowledge_base_id` bigint DEFAULT NULL,
  `status` int DEFAULT '0',
  `adopt` int DEFAULT '0',
  `modified_by` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_kb` (`knowledge_base_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `consolidated_cash_flow` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `file_id` bigint DEFAULT NULL,
  `file_name` varchar(512) DEFAULT NULL,
  `file_path` varchar(1024) DEFAULT NULL,
  `parsed_file_path` varchar(1024) DEFAULT NULL,
  `company_full_name` varchar(255) DEFAULT NULL,
  `company_short_name` varchar(255) DEFAULT NULL,
  `year` varchar(16) DEFAULT NULL,
  `period_type` varchar(32) DEFAULT NULL,
  `date_type` int DEFAULT NULL,
  `indicator_name` varchar(255) DEFAULT NULL,
  `indicator_raw` varchar(512) DEFAULT NULL,
  `indicator_value` varchar(255) DEFAULT NULL,
  `fixed_value` varchar(255) DEFAULT NULL,
  `indicator_unit` varchar(64) DEFAULT NULL,
  `indicator_value_position` text,
  `indicator_value_page_size` text,
  `indicator_value_offset` text,
  `indicator_value_page_number` text,
  `knowledge_base_name` varchar(255) DEFAULT NULL,
  `knowledge_base_id` bigint DEFAULT NULL,
  `status` int DEFAULT '0',
  `adopt` int DEFAULT '0',
  `modified_by` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_kb` (`knowledge_base_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `consolidated_income` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `file_id` bigint DEFAULT NULL,
  `file_name` varchar(512) DEFAULT NULL,
  `file_path` varchar(1024) DEFAULT NULL,
  `parsed_file_path` varchar(1024) DEFAULT NULL,
  `company_full_name` varchar(255) DEFAULT NULL,
  `company_short_name` varchar(255) DEFAULT NULL,
  `year` varchar(16) DEFAULT NULL,
  `period_type` varchar(32) DEFAULT NULL,
  `date_type` int DEFAULT NULL,
  `indicator_name` varchar(255) DEFAULT NULL,
  `indicator_raw` varchar(512) DEFAULT NULL,
  `indicator_value` varchar(255) DEFAULT NULL,
  `fixed_value` varchar(255) DEFAULT NULL,
  `indicator_unit` varchar(64) DEFAULT NULL,
  `indicator_value_position` text,
  `indicator_value_page_size` text,
  `indicator_value_offset` text,
  `indicator_value_page_number` text,
  `knowledge_base_name` varchar(255) DEFAULT NULL,
  `knowledge_base_id` bigint DEFAULT NULL,
  `status` int DEFAULT '0',
  `adopt` int DEFAULT '0',
  `modified_by` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_kb` (`knowledge_base_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `department_info` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` varchar(255) COLLATE utf8mb4_general_ci NOT NULL COMMENT '部门名称',
  `code` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '部门编码',
  `admin` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '部门管理员',
  `parent_id` bigint DEFAULT NULL COMMENT '上级部门ID',
  `status` tinyint DEFAULT '1' COMMENT '状态：0:待激活；1:正常（已激活）；-1:删除',
  `gmt_create` datetime NOT NULL COMMENT '创建时间',
  `gmt_modified` datetime NOT NULL COMMENT '修改时间',
  `create_by` varchar(255) COLLATE utf8mb4_general_ci NOT NULL COMMENT '创建人',
  `modify_by` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '修改人',
  `seq` int DEFAULT NULL COMMENT '顺序',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dept_privilege` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'id',
  `target_id` bigint NOT NULL COMMENT '目标id',
  `dept_id` bigint DEFAULT NULL COMMENT '部门id',
  `biz_type` int NOT NULL COMMENT '1:知识库;2:检索配置;3:模型',
  `permission` int NOT NULL COMMENT '0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限',
  `is_del` int DEFAULT '1' COMMENT '是否删除 -1 删除  1 正常 默认值1',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `gmt_modified` datetime DEFAULT NULL COMMENT '更新时间',
  `create_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `update_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '更新人',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='部门-数据权限关联';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dialogue` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `label` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '对话名称',
  `session_id` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '对话id',
  `status` int DEFAULT '1' COMMENT '状态 0:删除;1正常，默认值1',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `gmt_modified` datetime DEFAULT NULL COMMENT '更新时间',
  `create_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `update_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '更新人',
  `sys_type` int DEFAULT NULL COMMENT '系统类型：0.智能会话，1.知识索引,3 临时会话',
  `config` text COLLATE utf8mb4_general_ci COMMENT '配置信息',
  `config_id` bigint DEFAULT NULL COMMENT '检索配置id',
  `config_history` text COLLATE utf8mb4_general_ci COMMENT '检索配置历史信息',
  `kb_id` bigint DEFAULT NULL COMMENT '知识库id',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1077 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='对话表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `feedback` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `answer_id` bigint DEFAULT NULL COMMENT '答案id',
  `restult` int DEFAULT NULL COMMENT '0：踩；1：赞',
  `user_name` varchar(64) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '用户登录名',
  `user_realname` varchar(64) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '用户真实名称',
  `dept_name` varchar(30) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '部门名称',
  `user_phone` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '手机',
  `que_error` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '理解问题有误',
  `ans_poor` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '回答不佳',
  `format_error` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '格式问题',
  `harmful_info` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '有害信息',
  `othres` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '其他',
  `supplement_explain` text COLLATE utf8mb4_general_ci COMMENT '补充说明',
  `ideal_answer` text COLLATE utf8mb4_general_ci COMMENT '理想回答',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `gmt_modified` datetime DEFAULT NULL COMMENT '更新时间',
  `create_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `update_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '更新人',
  `is_del` int DEFAULT '1' COMMENT '是否删除 -1 删除  1 正常 默认值1',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='反馈表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `file_parse_task` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `kb_id` bigint NOT NULL COMMENT '知识库id',
  `kb_name` varchar(256) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '知识库名称',
  `file_id` bigint NOT NULL COMMENT '文件id',
  `file_name` varchar(256) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '文件库名称',
  `task_info` text COLLATE utf8mb4_general_ci COMMENT '任务详情',
  `status` int DEFAULT '1' COMMENT '状态 -1:删除 1:待处理 2:处理中,3:重试中 4: 成功 5: 处理失败',
  `start_time` timestamp NULL DEFAULT NULL COMMENT '解析开始时间',
  `end_time` timestamp NULL DEFAULT NULL COMMENT '解析结束时间',
  `retry_limit` int DEFAULT NULL COMMENT '重试限制次数',
  `retry_times` int DEFAULT '0' COMMENT '已经重试次数',
  `error_msg` text COLLATE utf8mb4_general_ci COMMENT '失败原因',
  `create_by` varchar(30) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `modify_by` varchar(30) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '修改人',
  `gmt_modified` datetime DEFAULT NULL COMMENT '修改时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=634 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `folder_info` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` varchar(512) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '文件夹名称',
  `kb_id` bigint DEFAULT NULL COMMENT '知识库id',
  `type` int DEFAULT NULL COMMENT '1:文档解析；2:FAQ抽取; 3;知识图谱 4:FAQ管理创建的文件夹或者从FAQ抽取复制的文件夹',
  `parent_id` bigint DEFAULT NULL COMMENT '父文件夹id',
  `folder_label` varchar(512) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '文件夹标签',
  `status` int DEFAULT '1' COMMENT '1：正常；-1：删除',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `gmt_modified` datetime DEFAULT NULL COMMENT '更新时间',
  `create_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `update_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '更新人',
  `full_path` varchar(2000) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '完整路径（包含结尾/)',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `group_info` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'id',
  `pid` bigint DEFAULT '0' COMMENT '父id',
  `name` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '机构组名称',
  `description` varchar(150) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '描述',
  `is_del` int DEFAULT '1' COMMENT '是否删除 -1 删除  1 正常 默认值1',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `gmt_modified` datetime DEFAULT NULL COMMENT '更新时间',
  `create_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `update_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '更新人',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='机构组';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `group_privilege` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'id',
  `target_id` bigint NOT NULL COMMENT '目标id',
  `group_id` bigint DEFAULT NULL COMMENT '机构组id',
  `biz_type` int NOT NULL COMMENT '1:知识库;2:检索配置',
  `permission` int NOT NULL COMMENT '0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限',
  `is_del` int DEFAULT '1' COMMENT '是否删除 -1 删除  1 正常 默认值1',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `gmt_modified` datetime DEFAULT NULL COMMENT '更新时间',
  `create_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `update_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '更新人',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='机构组-数据权限关联';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `interface_info` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `app_name` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '应用名称',
  `app_name_abbreviate` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '应用简称',
  `name` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '接口名称',
  `url` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'url',
  `method` varchar(16) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '接口的请求方式',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `gmt_modified` datetime DEFAULT NULL COMMENT '更新时间',
  `create_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `update_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '更新人',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2127620119 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='接口信息';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `kb_label_his` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `kb_id` bigint NOT NULL COMMENT '知识库id',
  `labe` text COLLATE utf8mb4_general_ci COMMENT '知识库使用的标签',
  `is_del` int DEFAULT '1' COMMENT '是否删除 -1 删除  1 正常 默认值1',
  `create_by` varchar(30) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `modify_by` varchar(30) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '修改人',
  `gmt_modified` datetime DEFAULT NULL COMMENT '修改时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `knowledge_base` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `kb_name` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '知识库名称',
  `primitive_name` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '知识库原始名称,对应算法知识库的名称',
  `kb_type` int DEFAULT '1' COMMENT '知识库类型 1:知识库 2: 文档上传问答',
  `kb_des` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '描述',
  `source_url` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '路径',
  `status` int DEFAULT '1' COMMENT '状态 0:删除;1正常，默认值1',
  `config` text COLLATE utf8mb4_general_ci COMMENT '知识库解析配置',
  `kb_label` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '知识库标签',
  `create_by` varchar(30) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `modify_by` varchar(30) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '修改人',
  `gmt_modified` datetime DEFAULT NULL COMMENT '修改时间',
  `platform` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '上层应用平台',
  `private_kb` int DEFAULT '0' COMMENT '是否私有知识库 0：非私有 1：私有',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1001 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='知识库';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `knowledge_base_list` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `kb_id` bigint NOT NULL COMMENT '知识库id',
  `file_id` varchar(64) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'minIO文件的id',
  `file_name` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '文件id',
  `file_size` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '文件大小',
  `file_path` varchar(256) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '路径',
  `full_text_path` varchar(256) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '全文txt路径',
  `status` int DEFAULT '1' COMMENT '状态 0:删除 1:正常 2:解析中，3:解析成功 4: 解析失败',
  `is_enable` int DEFAULT '1' COMMENT '0:禁用;1启用',
  `create_by` varchar(30) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `modify_by` varchar(30) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '修改人',
  `gmt_modified` datetime DEFAULT NULL COMMENT '修改时间',
  `parsed_file_path` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `parse_type` int DEFAULT '1' COMMENT '1 文件解析；2 FAQ解析 3 图解析；4 文档上传问答; 5 从文件解析复制的文件或者FAQ导入的问答对文件; 10 文件解析&faq抽取',
  `aq_count` int DEFAULT '0' COMMENT '问答对数',
  `faq_extract_status` int DEFAULT '1' COMMENT 'faq抽取状态 1 未抽取；2 抽取中 3 抽取成功 4 抽取失败',
  `graph_parse_status` int DEFAULT '1' COMMENT '图解析状态 1 未解析；2 解析中 3 解析成功 4 解析失败',
  `revise_date` varchar(30) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '修订实时间',
  `parent_file_name` varchar(127) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '父文件名称',
  `version` varchar(16) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '版本号',
  `converted_file_path` varchar(512) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '转化后的文件路径',
  `folder_id` bigint DEFAULT NULL COMMENT '文件夹id',
  `source_url` varchar(1000) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '文件url地址(从网页获取的文件)',
  `chunking` bit(1) DEFAULT NULL COMMENT '文件是否chunk化',
  `uid` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '文件的uid(uid是前端生成的,文档上传问答使用,通过uid来判断文件解析状态)',
  `temp_status` int DEFAULT '2' COMMENT '1 临时文件,2 持久化文件 默认值是2',
  `group_id` varchar(512) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '文件集群组id，算法端根据文件内容生成',
  `table_file_paths` longtext COLLATE utf8mb4_general_ci COMMENT '表格解析后的文件路径',
  `pid` bigint DEFAULT NULL COMMENT '针对于FAQ管理，文件中有文件',
  `image_paths` text COLLATE utf8mb4_general_ci COMMENT '图片解析路径',
  `chunk_type` varchar(32) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '切片策略',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=999011 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='知识库明细';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `model_info` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `model_name` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '模型名称',
  `type` tinyint DEFAULT '1' COMMENT '模型使用类型: 1:LLM大语言模型、2:Embedding嵌入、3:rerank排序、4:MultiModel图片解析',
  `model_protocol` tinyint DEFAULT NULL COMMENT '模型传输协议,1-Baichuan、2-Qwen、3-GLM、4-openAI',
  `model_ide` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '待接入的模型ID',
  `api_key` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'APIkey',
  `url` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '请求URL',
  `dec` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '说明',
  `status` tinyint DEFAULT NULL COMMENT '状态,0-不可用,1-可用,3-检测中',
  `error_msg` varchar(500) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '报错信息',
  `is_dtl` varchar(1) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '逻辑删除,0-未删除,1-已删除,默认为0',
  `thinking` int DEFAULT '0' COMMENT '推理思考(qwen3相关模型的功能) 0:没有推理思考功能 1:有推理思考功能',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `gmt_modified` datetime DEFAULT NULL COMMENT '更新时间',
  `create_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `update_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '更新人',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='模型信息表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `parse_task` (
  `task_id` varchar(64) NOT NULL,
  `pid` int DEFAULT NULL,
  `param` longtext,
  `status` varchar(8) DEFAULT NULL,
  `process_info` longtext,
  `minio_paths` longtext,
  `result` longtext,
  `create_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `update_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`task_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `question` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `gmt_modified` datetime DEFAULT NULL COMMENT '修改时间',
  `dialogue_id` bigint DEFAULT NULL COMMENT '对话id',
  `content` text COLLATE utf8mb4_general_ci COMMENT '答案内容',
  `type` varchar(32) COLLATE utf8mb4_general_ci DEFAULT '1' COMMENT 'TEXT：文本；VOICE：语音',
  `front_uuid` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '前端生成的uuid',
  `alg_model` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '模型算法',
  `alg_params` text COLLATE utf8mb4_general_ci COMMENT '模型参数(json)',
  `knowledge_base_name` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '知识库名称',
  `knowledge_params` text COLLATE utf8mb4_general_ci COMMENT '知识库参数(json)',
  `audio_url` varchar(512) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '音频地址',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1129 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='答案表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `re_embedding_file` (
  `id` bigint NOT NULL,
  `task_id` bigint DEFAULT NULL,
  `kb_id` bigint DEFAULT NULL,
  `kb_name` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `file_id` bigint DEFAULT NULL,
  `gmt_create` date DEFAULT NULL,
  `gmt_modified` date DEFAULT NULL,
  `total_chunk_num` bigint DEFAULT NULL,
  `processed_chunk_num` bigint DEFAULT NULL,
  `error_chunk_num` bigint DEFAULT NULL,
  `is_del` int DEFAULT NULL,
  `is_migrate` int DEFAULT NULL,
  `status` int DEFAULT NULL,
  `last_error` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `re_embedding_retry_task` (
  `id` bigint NOT NULL,
  `uid` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `task_id` bigint DEFAULT NULL,
  `type` int DEFAULT NULL,
  `payload` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `last_error` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `gmt_create` date DEFAULT NULL,
  `gmt_modified` date DEFAULT NULL,
  `retry_times` int DEFAULT NULL,
  `is_del` int DEFAULT NULL,
  `status` int DEFAULT NULL,
  `file_id` bigint DEFAULT NULL,
  `kb_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `re_embedding_task` (
  `id` bigint NOT NULL,
  `kb_id` bigint DEFAULT NULL,
  `kb_name` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `embedding_model_name` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `status` int DEFAULT NULL,
  `is_del` int DEFAULT NULL,
  `log_summary` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `gmt_modified` datetime DEFAULT NULL COMMENT '更新时间',
  `msg_key` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `total_file_num` bigint DEFAULT NULL,
  `uid` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `create_by` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `modified_by` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `resource_info` (
  `is_dtl` varchar(255) COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '逻辑删除 是否删除 1是 0否',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `create_by` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `gmt_modified` datetime DEFAULT NULL COMMENT '修改时间',
  `update_by` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '更新人',
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '名称',
  `url` varchar(2048) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '路径',
  `description` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '描述',
  `icon` varchar(200) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '图标',
  `pid` bigint DEFAULT NULL COMMENT '父类id',
  `seq` bigint DEFAULT NULL COMMENT '排序',
  `status` varchar(255) COLLATE utf8mb4_general_ci DEFAULT '1' COMMENT '状态 0 禁用 1 启用',
  `resource_type` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '菜单类型 1:菜单;2:接口',
  `code` varchar(64) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '编码',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='资源表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `resource_interface` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `resource_id` bigint DEFAULT NULL COMMENT '权限id',
  `interface_id` bigint DEFAULT NULL COMMENT '接口id',
  `is_del` int DEFAULT '1' COMMENT '是否删除 -1 删除  1 正常 默认值1',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `gmt_modified` datetime DEFAULT NULL COMMENT '更新时间',
  `create_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `update_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '更新人',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=534 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='权限接口关联';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `role_info` (
  `is_dtl` varchar(255) COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '逻辑删除 是否删除 1是 0否',
  `create_by` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '更新人',
  `gmt_modified` datetime DEFAULT NULL COMMENT '更新时间',
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '角色名称',
  `description` varchar(512) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '描述',
  `seq` bigint DEFAULT NULL COMMENT '排序',
  `status` int DEFAULT '1' COMMENT '状态 0 禁用 1 启用',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='角色表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `role_resource` (
  `is_dtl` varchar(255) COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '逻辑删除 是否删除 1是 0否',
  `create_by` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `update_by` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '更新人',
  `gmt_modified` datetime DEFAULT NULL COMMENT '更新时间',
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `role_id` bigint DEFAULT NULL COMMENT '角色id',
  `resource_id` bigint DEFAULT NULL COMMENT '资源id',
  `status` int DEFAULT '1' COMMENT '状态（1:启用; 0:禁用）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='角色-资源关系表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `search_config` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `status` int DEFAULT '1' COMMENT '状态 0:禁用；1:正常 默认值1',
  `is_default` int DEFAULT '1' COMMENT '是否默认 0:否；1:是 默认值1',
  `config_json` text COLLATE utf8mb4_general_ci COMMENT '配置详情',
  `name` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '名称',
  `des` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '描述',
  `create_by` varchar(30) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `modify_by` varchar(30) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '修改人',
  `gmt_modified` datetime DEFAULT NULL COMMENT '修改时间',
  `sensitive_word_ids` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '敏感词id',
  `default_answer` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '默认回答(sensitive_word_ids不为空时,必填)',
  `enabled_faq` int DEFAULT '0' COMMENT '是否开启faq(0:否;1:是)',
  `depend_on_kb` int DEFAULT '0' COMMENT '是否强依赖知识库(0:否;1:是)',
  `is_del` int DEFAULT '1' COMMENT '是否删除 -1 删除  1 正常 默认值1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_search_config_default` (((case when ((`is_default` = 1) and (`is_del` = 1)) then 1 else NULL end)))
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='问题查询配置表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sensitive_words` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `gmt_modified` datetime DEFAULT NULL COMMENT '修改时间',
  `name` varchar(512) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '敏感词库名称',
  `descript` varchar(512) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '描述',
  `words` longtext COLLATE utf8mb4_general_ci COMMENT '敏感词详情',
  `status` int DEFAULT NULL COMMENT '状态，1正常，-1删除',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `syn_log` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `kb_id` bigint DEFAULT NULL COMMENT '知识库id',
  `target_id` bigint DEFAULT NULL COMMENT '目标id（知识库id）',
  `log_type` int DEFAULT NULL COMMENT '日志类型 1:文件解析;2FAQ抽取',
  `error_code` varchar(16) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '异常码 (如果为-1的话，接口不可用)',
  `error_message` text COLLATE utf8mb4_general_ci COMMENT '异常信息',
  `error_detail` text COLLATE utf8mb4_general_ci COMMENT '异常信息详情',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `gmt_modified` datetime DEFAULT NULL COMMENT '更新时间',
  `create_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `update_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '更新人',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=709 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='日志';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tools_database` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'ä¸»é”®',
  `name` varchar(128) DEFAULT NULL COMMENT 'æ•°æ®åº“åç§°',
  `description` varchar(512) DEFAULT NULL COMMENT 'æè¿°',
  `datasource_type` varchar(32) DEFAULT NULL COMMENT 'æ•°æ®æºç±»åž‹ DataTable/DirectDB',
  `db_type` varchar(32) DEFAULT NULL COMMENT 'æ•°æ®åº“ç±»åž‹',
  `db_host` varchar(128) DEFAULT NULL COMMENT 'ä¸»æœº',
  `db_port` int DEFAULT NULL COMMENT 'ç«¯å£',
  `db_database` varchar(128) DEFAULT NULL COMMENT 'åº“å',
  `db_user` varchar(128) DEFAULT NULL COMMENT 'è´¦å·',
  `db_password` varchar(512) DEFAULT NULL COMMENT 'å¯†ç (å¯†æ–‡)',
  `jdbc_url` varchar(512) DEFAULT NULL COMMENT 'JDBC URL',
  `jdbc_driver_class` varchar(255) DEFAULT NULL COMMENT 'é©±åŠ¨ç±»',
  `gmt_create` datetime DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `create_by` varchar(64) DEFAULT NULL,
  `update_by` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='ç»“æž„åŒ–æŸ¥è¯¢-æ•°æ®åº“é…ç½®';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tools_table` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `database_id` bigint DEFAULT NULL COMMENT 'æ‰€å±žæ•°æ®åº“',
  `business_name` varchar(255) DEFAULT NULL COMMENT 'ä¸šåŠ¡å',
  `physical_name` varchar(255) DEFAULT NULL COMMENT 'ç‰©ç†è¡¨å',
  `description` text COMMENT 'è¡¨æè¿°',
  `column_count` int DEFAULT '0',
  `row_count` bigint DEFAULT '0',
  `gmt_create` datetime DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `create_by` varchar(64) DEFAULT NULL,
  `update_by` varchar(64) DEFAULT NULL,
  `is_gen_desc` tinyint(1) DEFAULT '0',
  `gen_desc_err_msg` varchar(1024) DEFAULT NULL,
  `gen_desc_status` varchar(32) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_db` (`database_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='ç»“æž„åŒ–æŸ¥è¯¢-è¡¨å…ƒæ•°æ®';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tools_table_column` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `database_id` bigint DEFAULT NULL,
  `table_id` bigint DEFAULT NULL,
  `business_name` varchar(255) DEFAULT NULL,
  `physical_name` varchar(255) DEFAULT NULL,
  `description` varchar(1024) DEFAULT NULL,
  `data_type` varchar(128) DEFAULT NULL,
  `gmt_create` datetime DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `create_by` varchar(64) DEFAULT NULL,
  `update_by` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_tbl` (`table_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='ç»“æž„åŒ–æŸ¥è¯¢-å­—æ®µå…ƒæ•°æ®';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tools_table_file` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `database_id` bigint DEFAULT NULL,
  `table_id` bigint DEFAULT NULL,
  `original_filename` varchar(255) DEFAULT NULL,
  `folder_path` varchar(512) DEFAULT NULL,
  `file_name` varchar(255) DEFAULT NULL,
  `object_name` varchar(512) DEFAULT NULL,
  `file_path` varchar(512) DEFAULT NULL,
  `file_size` double DEFAULT NULL,
  `column_count` int DEFAULT '0',
  `row_count` bigint DEFAULT '0',
  `status` varchar(32) DEFAULT NULL,
  `use_time` bigint DEFAULT NULL,
  `error_msg` varchar(1024) DEFAULT NULL,
  `gmt_create` datetime DEFAULT CURRENT_TIMESTAMP,
  `gmt_modified` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `create_by` varchar(64) DEFAULT NULL,
  `update_by` varchar(64) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_db` (`database_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='ç»“æž„åŒ–æŸ¥è¯¢-ä¸Šä¼ æ–‡ä»¶';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_group` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'id',
  `user_id` bigint DEFAULT NULL COMMENT '用户id',
  `group_id` bigint DEFAULT NULL COMMENT '机构分组id',
  `dept_id` bigint DEFAULT NULL COMMENT '部门id',
  `is_del` int DEFAULT '1' COMMENT '是否删除 -1 删除  1 正常 默认值1',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `gmt_modified` datetime DEFAULT NULL COMMENT '更新时间',
  `create_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `update_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '更新人',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='机构-用户关联表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_info` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_name` varchar(128) COLLATE utf8mb4_general_ci NOT NULL COMMENT '用户名',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `gmt_modified` datetime DEFAULT NULL COMMENT '更新时间',
  `create_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `update_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '更新人',
  `is_dtl` varchar(255) COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '逻辑删除 是否删除 1是 0 未删除',
  `user_password` varchar(512) COLLATE utf8mb4_general_ci NOT NULL COMMENT '密码',
  `user_realname` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '真实姓名',
  `user_email` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '邮箱',
  `url` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '用户头像',
  `user_phone` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '手机',
  `status` int DEFAULT '1' COMMENT '状态  1启用 0禁用',
  `expire_time` datetime DEFAULT NULL COMMENT '过期时间',
  `miss_num` int DEFAULT '0' COMMENT '密码错误次数',
  `password_updated` datetime DEFAULT NULL COMMENT '密码更改时间',
  `admin_reset_password` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '管理员重置的密码',
  `ip` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'ip',
  `online_time` datetime DEFAULT NULL COMMENT '上线时间',
  `organization_id` bigint DEFAULT NULL COMMENT '机构id',
  `emp_no` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '用户工号',
  `dept_id` varchar(30) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '部门id',
  `dept_name` varchar(30) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '部门名称(冗余字段)',
  `app_key` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '认证key',
  `resign_date` datetime DEFAULT NULL COMMENT '离职日期',
  `feature` varchar(1000) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '用户特征',
  `system_source` int DEFAULT NULL COMMENT '用户来源',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='用户表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_operate` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `gmt_created` datetime DEFAULT NULL COMMENT '创建时间',
  `gmt_modified` datetime DEFAULT NULL COMMENT '创建时间',
  `name` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '方法名称',
  `url` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '方法url',
  `start_time` datetime DEFAULT NULL COMMENT '接口请求开始时间',
  `end_time` datetime DEFAULT NULL COMMENT '接口请求结束时间',
  `user_id` bigint DEFAULT NULL COMMENT '用户id',
  `user_name` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '用户名称',
  `params` text COLLATE utf8mb4_general_ci COMMENT '参数',
  `ip` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'ip',
  `success` int DEFAULT NULL COMMENT '接口是否请求成功 0 否  1是 默认值1',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2116211029455855619 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_privilege` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'id',
  `target_id` bigint NOT NULL COMMENT '配置id',
  `user_id` bigint DEFAULT NULL COMMENT '用户id,-1代表所有人',
  `biz_type` int NOT NULL COMMENT '1:知识库;2:检索配置;3:模型',
  `permission` int NOT NULL COMMENT '0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限',
  `is_del` int DEFAULT '1' COMMENT '是否删除 -1 删除  1 正常 默认值1',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `gmt_modified` datetime DEFAULT NULL COMMENT '更新时间',
  `create_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `update_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '更新人',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=137 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='用户-数据权限关联';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_role` (
  `is_dtl` varchar(255) COLLATE utf8mb4_general_ci DEFAULT '0' COMMENT '逻辑删除 是否删除 1是 0 否',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `gmt_modified` datetime DEFAULT NULL COMMENT '更新时间',
  `create_by` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `update_by` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '更新人',
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `role_id` bigint NOT NULL COMMENT '角色id',
  `user_id` bigint NOT NULL COMMENT '用户id',
  `status` int DEFAULT '1' COMMENT '状态(1:启用; 0:禁用)',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=62 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='用户-角色关系表';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_security_question` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键编号',
  `user_id` bigint DEFAULT NULL COMMENT '用户编号',
  `question` varchar(500) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '问题',
  `answer` varchar(500) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '答案',
  `gmt_create` datetime DEFAULT NULL COMMENT '创建时间',
  `gmt_modified` datetime DEFAULT NULL COMMENT '更新时间',
  `create_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '创建人',
  `update_by` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '更新人',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='user_security_question';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

