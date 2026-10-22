
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
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '修改时间（原 gmt_modified）',
  `dialogue_id` bigint DEFAULT NULL COMMENT '对话id',
  `question_id` bigint DEFAULT NULL COMMENT '问题id',
  `content` text COMMENT '答案内容',
  `type` varchar(32) DEFAULT '1' COMMENT 'TEXT：文本；VOICE：语音',
  `reference` mediumblob COMMENT '参考内容(json)',
  `database_reference` text COMMENT '数据库召回',
  `log_result` text COMMENT '算法评测日志(json)',
  `retrieve_recall_Param` text COMMENT '知识检索召回测试的参数',
  `recommend_question` text COMMENT '问题推荐',
  `llm_type` int DEFAULT '1' COMMENT '推理类型 1:推理接口, 2:表格推理接口 默认值1',
  `result_type` int DEFAULT NULL,
  `resp_time` bigint DEFAULT NULL COMMENT '问答接口响应时间(毫秒)',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `api_key_info` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `api_key` varchar(512) NOT NULL COMMENT 'apikey全局唯一',
  `target_id` int DEFAULT NULL COMMENT '目标id',
  `status` int DEFAULT '1' COMMENT '状态 0:禁用；1:正常 默认值1',
  `biz_type` tinyint NOT NULL DEFAULT '1' COMMENT '业务类型 1:助手配置',
  `expire_time` datetime(3) NOT NULL COMMENT '过期时间',
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否删除 -1 删除  1 正常 默认值1（原 is_del）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_by` varchar(64) NOT NULL COMMENT '修改人（原 modify_by）',
  `updated_at` datetime(3) NOT NULL COMMENT '修改时间（原 gmt_modified）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `biz_label` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'id',
  `target_id` bigint NOT NULL COMMENT '资源id',
  `label` varchar(256) NOT NULL COMMENT 'label',
  `biz_type` tinyint NOT NULL,
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` varchar(64) NOT NULL COMMENT '更新人（原 update_by）',
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否删除 -1 删除  1 正常 默认值1（原 is_del）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `department_info` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` varchar(255) NOT NULL COMMENT '部门名称',
  `code` varchar(255) DEFAULT NULL COMMENT '部门编码',
  `admin` varchar(255) DEFAULT NULL COMMENT '部门管理员',
  `parent_id` bigint DEFAULT NULL COMMENT '上级部门ID',
  `status` tinyint DEFAULT '1' COMMENT '状态：0:待激活；1:正常（已激活）；-1:删除',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '修改时间（原 gmt_modified）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` varchar(64) NOT NULL COMMENT '修改人（原 modify_by）',
  `seq` int DEFAULT NULL COMMENT '顺序',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dept_privilege` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'id',
  `target_id` bigint NOT NULL COMMENT '目标id',
  `dept_id` bigint DEFAULT NULL COMMENT '部门id',
  `biz_type` int DEFAULT NULL,
  `permission` int NOT NULL COMMENT '0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限',
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否删除 -1 删除  1 正常 默认值1（原 is_del）',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` varchar(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dialogue` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `label` varchar(255) DEFAULT NULL COMMENT '对话名称',
  `session_id` varchar(128) DEFAULT NULL COMMENT '对话id',
  `status` int DEFAULT NULL,
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` varchar(64) NOT NULL COMMENT '更新人（原 update_by）',
  `sys_type` int DEFAULT NULL COMMENT '系统类型：0.智能会话，1.知识索引,3 临时会话',
  `config` text COMMENT '配置信息',
  `config_id` bigint DEFAULT NULL COMMENT '检索配置id',
  `config_history` text COMMENT '检索配置历史信息',
  `kb_id` bigint DEFAULT NULL COMMENT '知识库id',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `feedback` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `answer_id` bigint DEFAULT NULL COMMENT '答案id',
  `restult` int DEFAULT NULL COMMENT '0：踩；1：赞',
  `user_name` varchar(64) DEFAULT NULL COMMENT '用户登录名',
  `user_realname` varchar(64) DEFAULT NULL COMMENT '用户真实名称',
  `dept_name` varchar(30) DEFAULT NULL COMMENT '部门名称',
  `user_phone` varchar(20) DEFAULT NULL COMMENT '手机',
  `que_error` varchar(255) DEFAULT NULL COMMENT '理解问题有误',
  `ans_poor` varchar(255) DEFAULT NULL COMMENT '回答不佳',
  `format_error` varchar(255) DEFAULT NULL COMMENT '格式问题',
  `harmful_info` varchar(255) DEFAULT NULL COMMENT '有害信息',
  `othres` varchar(255) DEFAULT NULL COMMENT '其他',
  `supplement_explain` text COMMENT '补充说明',
  `ideal_answer` text COMMENT '理想回答',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` varchar(64) NOT NULL COMMENT '更新人（原 update_by）',
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否删除 -1 删除  1 正常 默认值1（原 is_del）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `file_parse_task` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `kb_id` bigint NOT NULL COMMENT '知识库id',
  `kb_name` varchar(256) DEFAULT NULL COMMENT '知识库名称',
  `file_id` bigint NOT NULL COMMENT '文件id',
  `file_name` varchar(256) DEFAULT NULL COMMENT '文件库名称',
  `task_info` text COMMENT '任务详情',
  `status` int DEFAULT '1' COMMENT '状态 -1:删除 1:待处理 2:处理中,3:重试中 4: 成功 5: 处理失败',
  `start_time` timestamp NULL DEFAULT NULL COMMENT '解析开始时间',
  `end_time` timestamp NULL DEFAULT NULL COMMENT '解析结束时间',
  `retry_limit` int DEFAULT NULL COMMENT '重试限制次数',
  `retry_times` int DEFAULT '0' COMMENT '已经重试次数',
  `error_msg` text COMMENT '失败原因',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_by` varchar(64) NOT NULL COMMENT '修改人（原 modify_by）',
  `updated_at` datetime(3) NOT NULL COMMENT '修改时间（原 gmt_modified）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `folder_info` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` varchar(512) DEFAULT NULL COMMENT '文件夹名称',
  `kb_id` bigint DEFAULT NULL COMMENT '知识库id',
  `type` int DEFAULT NULL,
  `parent_id` bigint DEFAULT NULL COMMENT '父文件夹id',
  `folder_label` varchar(512) DEFAULT NULL COMMENT '文件夹标签',
  `status` int DEFAULT '1' COMMENT '1：正常；-1：删除',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` varchar(64) NOT NULL COMMENT '更新人（原 update_by）',
  `full_path` varchar(2000) DEFAULT NULL COMMENT '完整路径（包含结尾/)',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `group_info` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'id',
  `pid` bigint DEFAULT '0' COMMENT '父id',
  `name` varchar(50) DEFAULT NULL COMMENT '机构组名称',
  `description` varchar(150) DEFAULT NULL COMMENT '描述',
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否删除 -1 删除  1 正常 默认值1（原 is_del）',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` varchar(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `group_privilege` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'id',
  `target_id` bigint NOT NULL COMMENT '目标id',
  `group_id` bigint DEFAULT NULL COMMENT '机构组id',
  `biz_type` int DEFAULT NULL,
  `permission` int NOT NULL COMMENT '0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限',
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否删除 -1 删除  1 正常 默认值1（原 is_del）',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` varchar(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `interface_info` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `app_name` varchar(128) DEFAULT NULL COMMENT '应用名称',
  `app_name_abbreviate` varchar(128) DEFAULT NULL COMMENT '应用简称',
  `name` varchar(128) DEFAULT NULL COMMENT '接口名称',
  `url` varchar(128) DEFAULT NULL COMMENT 'url',
  `method` varchar(16) DEFAULT NULL COMMENT '接口的请求方式',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` varchar(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `kb_label_his` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `kb_id` bigint NOT NULL COMMENT '知识库id',
  `labe` text COMMENT '知识库使用的标签',
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否删除 -1 删除  1 正常 默认值1（原 is_del）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_by` varchar(64) NOT NULL COMMENT '修改人（原 modify_by）',
  `updated_at` datetime(3) NOT NULL COMMENT '修改时间（原 gmt_modified）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `knowledge_base` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `kb_name` varchar(128) DEFAULT NULL COMMENT '知识库名称',
  `primitive_name` varchar(128) DEFAULT NULL COMMENT '知识库原始名称,对应算法知识库的名称',
  `kb_type` int DEFAULT '1' COMMENT '知识库类型 1:知识库 2: 文档上传问答',
  `kb_des` varchar(255) DEFAULT NULL COMMENT '描述',
  `source_url` varchar(128) DEFAULT NULL COMMENT '路径',
  `status` int DEFAULT NULL,
  `config` text COMMENT '知识库解析配置',
  `kb_label` varchar(128) DEFAULT NULL COMMENT '知识库标签',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_by` varchar(64) NOT NULL COMMENT '修改人（原 modify_by）',
  `updated_at` datetime(3) NOT NULL COMMENT '修改时间（原 gmt_modified）',
  `platform` varchar(128) DEFAULT NULL COMMENT '上层应用平台',
  `private_kb` int DEFAULT '0' COMMENT '是否私有知识库 0：非私有 1：私有',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `knowledge_base_list` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `kb_id` bigint NOT NULL COMMENT '知识库id',
  `file_id` varchar(64) DEFAULT NULL COMMENT 'minIO文件的id',
  `file_name` varchar(128) DEFAULT NULL COMMENT '文件id',
  `file_size` varchar(255) DEFAULT NULL COMMENT '文件大小',
  `file_path` varchar(256) DEFAULT NULL COMMENT '路径',
  `full_text_path` varchar(256) DEFAULT NULL COMMENT '全文txt路径',
  `status` int DEFAULT '1' COMMENT '状态 0:删除 1:正常 2:解析中，3:解析成功 4: 解析失败',
  `is_enable` int DEFAULT NULL,
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_by` varchar(64) NOT NULL COMMENT '修改人（原 modify_by）',
  `updated_at` datetime(3) NOT NULL COMMENT '修改时间（原 gmt_modified）',
  `parsed_file_path` varchar(255) DEFAULT NULL,
  `parse_type` int DEFAULT NULL,
  `aq_count` int DEFAULT '0' COMMENT '问答对数',
  `faq_extract_status` int DEFAULT '1' COMMENT 'faq抽取状态 1 未抽取；2 抽取中 3 抽取成功 4 抽取失败',
  `graph_parse_status` int DEFAULT '1' COMMENT '图解析状态 1 未解析；2 解析中 3 解析成功 4 解析失败',
  `revise_date` varchar(30) DEFAULT NULL COMMENT '修订实时间',
  `parent_file_name` varchar(127) DEFAULT NULL COMMENT '父文件名称',
  `version` varchar(16) DEFAULT NULL COMMENT '版本号',
  `converted_file_path` varchar(512) DEFAULT NULL COMMENT '转化后的文件路径',
  `folder_id` bigint DEFAULT NULL COMMENT '文件夹id',
  `source_url` varchar(1000) DEFAULT NULL COMMENT '文件url地址(从网页获取的文件)',
  `chunking` tinyint DEFAULT NULL COMMENT '文件是否chunk化',
  `uid` varchar(128) DEFAULT NULL COMMENT '文件的uid(uid是前端生成的,文档上传问答使用,通过uid来判断文件解析状态)',
  `temp_status` int DEFAULT '2' COMMENT '1 临时文件,2 持久化文件 默认值是2',
  `group_id` varchar(512) DEFAULT NULL COMMENT '文件集群组id，算法端根据文件内容生成',
  `table_file_paths` longtext COMMENT '表格解析后的文件路径',
  `pid` bigint DEFAULT NULL COMMENT '针对于FAQ管理，文件中有文件',
  `image_paths` text COMMENT '图片解析路径',
  `chunk_type` varchar(32) DEFAULT NULL COMMENT '切片策略',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `model_info` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `model_name` varchar(128) DEFAULT NULL COMMENT '模型名称',
  `type` tinyint DEFAULT '1' COMMENT '模型使用类型: 1:LLM大语言模型、2:Embedding嵌入、3:rerank排序、4:MultiModel图片解析',
  `model_protocol` tinyint DEFAULT NULL COMMENT '模型传输协议,1-Baichuan、2-Qwen、3-GLM、4-openAI',
  `model_ide` varchar(128) DEFAULT NULL COMMENT '待接入的模型ID',
  `api_key` varchar(255) DEFAULT NULL COMMENT 'APIkey',
  `url` varchar(255) DEFAULT NULL COMMENT '请求URL',
  `dec` varchar(255) DEFAULT NULL COMMENT '说明',
  `status` tinyint DEFAULT NULL COMMENT '状态,0-不可用,1-可用,3-检测中',
  `error_msg` varchar(500) DEFAULT NULL COMMENT '报错信息',
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '逻辑删除,0-未删除,1-已删除,默认为0（原 is_dtl）',
  `thinking` int DEFAULT '0' COMMENT '推理思考(qwen3相关模型的功能) 0:没有推理思考功能 1:有推理思考功能',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` varchar(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `question` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '修改时间（原 gmt_modified）',
  `dialogue_id` bigint DEFAULT NULL COMMENT '对话id',
  `content` text COMMENT '答案内容',
  `type` varchar(32) DEFAULT '1' COMMENT 'TEXT：文本；VOICE：语音',
  `front_uuid` varchar(128) DEFAULT NULL COMMENT '前端生成的uuid',
  `alg_model` varchar(128) DEFAULT NULL COMMENT '模型算法',
  `alg_params` text COMMENT '模型参数(json)',
  `knowledge_base_name` varchar(128) DEFAULT NULL COMMENT '知识库名称',
  `knowledge_params` text COMMENT '知识库参数(json)',
  `audio_url` varchar(512) DEFAULT NULL COMMENT '音频地址',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `re_embedding_file` (
  `id` bigint NOT NULL,
  `task_id` bigint DEFAULT NULL,
  `kb_id` bigint DEFAULT NULL,
  `kb_name` varchar(255) DEFAULT NULL,
  `file_id` bigint DEFAULT NULL,
  `created_at` datetime(3) NOT NULL COMMENT '（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '（原 gmt_modified）',
  `total_chunk_num` bigint DEFAULT NULL,
  `processed_chunk_num` bigint DEFAULT NULL,
  `error_chunk_num` bigint DEFAULT NULL,
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '（原 is_del）',
  `is_migrate` int DEFAULT NULL,
  `status` int DEFAULT NULL,
  `last_error` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `re_embedding_retry_task` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `uid` varchar(255) DEFAULT NULL,
  `task_id` bigint DEFAULT NULL,
  `type` int DEFAULT NULL,
  `payload` varchar(255) DEFAULT NULL,
  `last_error` varchar(255) DEFAULT NULL,
  `created_at` datetime(3) NOT NULL COMMENT '（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '（原 gmt_modified）',
  `retry_times` int DEFAULT NULL,
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '（原 is_del）',
  `status` int DEFAULT NULL,
  `file_id` bigint DEFAULT NULL,
  `kb_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `re_embedding_task` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `kb_id` bigint DEFAULT NULL,
  `kb_name` varchar(255) DEFAULT NULL,
  `embedding_model_name` varchar(255) DEFAULT NULL,
  `status` int DEFAULT NULL,
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '（原 is_del）',
  `log_summary` varchar(255) DEFAULT NULL,
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `msg_key` varchar(255) DEFAULT NULL,
  `total_file_num` bigint DEFAULT NULL,
  `uid` varchar(255) DEFAULT NULL,
  `created_by` varchar(64) NOT NULL COMMENT '（原 create_by）',
  `modified_by` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `resource_info` (
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '逻辑删除 是否删除 1是 0否（原 is_dtl）',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_at` datetime(3) NOT NULL COMMENT '修改时间（原 gmt_modified）',
  `updated_by` varchar(64) NOT NULL COMMENT '更新人（原 update_by）',
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` varchar(128) DEFAULT NULL COMMENT '名称',
  `url` varchar(2048) DEFAULT NULL COMMENT '路径',
  `description` varchar(128) DEFAULT NULL COMMENT '描述',
  `icon` varchar(200) DEFAULT NULL COMMENT '图标',
  `pid` bigint DEFAULT NULL COMMENT '父类id',
  `seq` bigint DEFAULT NULL COMMENT '排序',
  `status` varchar(255) DEFAULT '1' COMMENT '状态 0 禁用 1 启用',
  `resource_type` varchar(255) DEFAULT NULL,
  `code` varchar(64) DEFAULT NULL COMMENT '编码',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `resource_interface` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `resource_id` bigint DEFAULT NULL COMMENT '权限id',
  `interface_id` bigint DEFAULT NULL COMMENT '接口id',
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否删除 -1 删除  1 正常 默认值1（原 is_del）',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` varchar(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `role_info` (
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '逻辑删除 是否删除 1是 0否（原 is_dtl）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_by` varchar(64) NOT NULL COMMENT '更新人（原 update_by）',
  `updated_at` datetime(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` varchar(128) DEFAULT NULL COMMENT '角色名称',
  `description` varchar(512) DEFAULT NULL COMMENT '描述',
  `seq` bigint DEFAULT NULL COMMENT '排序',
  `status` int DEFAULT '1' COMMENT '状态 0 禁用 1 启用',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `role_resource` (
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '逻辑删除 是否删除 1是 0否（原 is_dtl）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_by` varchar(64) NOT NULL COMMENT '更新人（原 update_by）',
  `updated_at` datetime(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `role_id` bigint DEFAULT NULL COMMENT '角色id',
  `resource_id` bigint DEFAULT NULL COMMENT '资源id',
  `status` int DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `search_config` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `status` int DEFAULT '1' COMMENT '状态 0:禁用；1:正常 默认值1',
  `is_default` int DEFAULT '1' COMMENT '是否默认 0:否；1:是 默认值1',
  `config_json` text COMMENT '配置详情',
  `name` varchar(50) DEFAULT NULL COMMENT '名称',
  `des` varchar(255) DEFAULT NULL COMMENT '描述',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_by` varchar(64) NOT NULL COMMENT '修改人（原 modify_by）',
  `updated_at` datetime(3) NOT NULL COMMENT '修改时间（原 gmt_modified）',
  `sensitive_word_ids` varchar(255) DEFAULT NULL COMMENT '敏感词id',
  `default_answer` varchar(255) DEFAULT NULL COMMENT '默认回答(sensitive_word_ids不为空时,必填)',
  `enabled_faq` int DEFAULT '0',
  `depend_on_kb` int DEFAULT '0',
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否删除 -1 删除  1 正常 默认值1（原 is_del）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sensitive_words` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '修改时间（原 gmt_modified）',
  `name` varchar(512) DEFAULT NULL COMMENT '敏感词库名称',
  `descript` varchar(512) DEFAULT NULL COMMENT '描述',
  `words` longtext COMMENT '敏感词详情',
  `status` int DEFAULT NULL COMMENT '状态，1正常，-1删除',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `syn_log` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `kb_id` bigint DEFAULT NULL COMMENT '知识库id',
  `target_id` bigint DEFAULT NULL COMMENT '目标id（知识库id）',
  `log_type` int DEFAULT NULL,
  `error_code` varchar(16) DEFAULT NULL COMMENT '异常码 (如果为-1的话，接口不可用)',
  `error_message` text COMMENT '异常信息',
  `error_detail` text COMMENT '异常信息详情',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` varchar(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tools_database` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `name` varchar(100) DEFAULT NULL COMMENT '数据库名称',
  `description` varchar(500) DEFAULT NULL COMMENT '数据库描述',
  `datasource_type` varchar(32) DEFAULT NULL COMMENT '数据源类型',
  `db_type` varchar(32) DEFAULT NULL COMMENT '数据库类型',
  `db_host` varchar(255) DEFAULT NULL COMMENT '连接地址',
  `db_port` int DEFAULT NULL COMMENT '连接端口',
  `db_database` varchar(100) DEFAULT NULL COMMENT '数据库名称',
  `db_user` varchar(100) DEFAULT NULL COMMENT '连接用户',
  `db_password` varchar(255) DEFAULT NULL COMMENT '连接密码',
  `jdbc_url` varchar(500) DEFAULT NULL COMMENT 'jdbc连接地址',
  `jdbc_driver_class` varchar(255) DEFAULT NULL COMMENT 'jdbc驱动类名',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` varchar(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tools_table` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `database_id` bigint DEFAULT NULL COMMENT '数据库编号',
  `business_name` varchar(100) DEFAULT NULL COMMENT '业务表名',
  `physical_name` varchar(100) DEFAULT NULL COMMENT '物理表名',
  `description` varchar(3000) DEFAULT NULL COMMENT '表描述',
  `column_count` int DEFAULT NULL COMMENT '列数量',
  `row_count` bigint DEFAULT NULL COMMENT '行数量',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` varchar(64) NOT NULL COMMENT '更新人（原 update_by）',
  `is_gen_desc` tinyint DEFAULT NULL COMMENT '更新人',
  `gen_desc_err_msg` varchar(1024) DEFAULT NULL COMMENT '更新人',
  `gen_desc_status` varchar(16) DEFAULT NULL COMMENT '更新人',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tools_table_column` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `database_id` bigint DEFAULT NULL COMMENT '数据库编号',
  `table_id` bigint DEFAULT NULL COMMENT '数据表编号',
  `business_name` varchar(100) DEFAULT NULL COMMENT '业务列名',
  `physical_name` varchar(100) DEFAULT NULL COMMENT '物理列名',
  `description` varchar(500) DEFAULT NULL COMMENT '列描述',
  `data_type` varchar(50) DEFAULT NULL COMMENT '数据类型',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` varchar(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tools_table_file` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `database_id` bigint DEFAULT NULL COMMENT '数据库编号',
  `table_id` bigint DEFAULT NULL COMMENT '数据表编号',
  `original_filename` varchar(255) DEFAULT NULL COMMENT '原始文件名称',
  `folder_path` varchar(255) DEFAULT NULL COMMENT '存储文件夹路径',
  `file_name` varchar(255) DEFAULT NULL COMMENT '文件名称',
  `object_name` varchar(255) DEFAULT NULL COMMENT '存储对象名称',
  `file_path` varchar(255) DEFAULT NULL COMMENT '文件路径',
  `file_size` double DEFAULT NULL COMMENT '文件大小',
  `column_count` int DEFAULT NULL COMMENT '列数量',
  `row_count` bigint DEFAULT NULL COMMENT '行数量',
  `status` varchar(255) DEFAULT NULL COMMENT '解析状态',
  `use_time` bigint DEFAULT NULL COMMENT '解析耗时(毫秒)',
  `error_msg` varchar(1000) DEFAULT NULL COMMENT '错误信息',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` varchar(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_group` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'id',
  `user_id` bigint DEFAULT NULL COMMENT '用户id',
  `group_id` bigint DEFAULT NULL COMMENT '机构分组id',
  `dept_id` bigint DEFAULT NULL COMMENT '部门id',
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否删除 -1 删除  1 正常 默认值1（原 is_del）',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` varchar(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_info` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `user_name` varchar(128) NOT NULL COMMENT '用户名',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` varchar(64) NOT NULL COMMENT '更新人（原 update_by）',
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '逻辑删除 是否删除 1是 0 未删除（原 is_dtl）',
  `user_password` varchar(512) NOT NULL COMMENT '密码',
  `user_realname` varchar(128) DEFAULT NULL COMMENT '真实姓名',
  `user_email` varchar(128) DEFAULT NULL COMMENT '邮箱',
  `url` varchar(255) DEFAULT NULL COMMENT '用户头像',
  `user_phone` varchar(20) DEFAULT NULL COMMENT '手机',
  `status` int DEFAULT '1' COMMENT '状态  1启用 0禁用',
  `expire_time` datetime(3) DEFAULT NULL COMMENT '过期时间',
  `miss_num` int DEFAULT '0' COMMENT '密码错误次数',
  `password_updated` datetime(3) DEFAULT NULL COMMENT '密码更改时间',
  `admin_reset_password` varchar(128) DEFAULT NULL COMMENT '管理员重置的密码',
  `ip` varchar(50) DEFAULT NULL COMMENT 'ip',
  `online_time` datetime(3) DEFAULT NULL COMMENT '上线时间',
  `organization_id` bigint DEFAULT NULL COMMENT '机构id',
  `emp_no` varchar(128) DEFAULT NULL COMMENT '用户工号',
  `dept_id` varchar(30) DEFAULT NULL COMMENT '部门id',
  `dept_name` varchar(30) DEFAULT NULL COMMENT '部门名称(冗余字段)',
  `app_key` varchar(128) DEFAULT NULL COMMENT '认证key',
  `resign_date` datetime(3) DEFAULT NULL COMMENT '离职日期',
  `feature` varchar(1000) DEFAULT NULL COMMENT '用户特征',
  `system_source` int DEFAULT NULL COMMENT '用户来源',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_operate` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `gmt_created` datetime(3) DEFAULT NULL COMMENT '创建时间',
  `updated_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_modified）',
  `name` varchar(255) DEFAULT NULL COMMENT '方法名称',
  `url` varchar(255) DEFAULT NULL COMMENT '方法url',
  `start_time` datetime(3) DEFAULT NULL COMMENT '接口请求开始时间',
  `end_time` datetime(3) DEFAULT NULL COMMENT '接口请求结束时间',
  `user_id` bigint DEFAULT NULL COMMENT '用户id',
  `user_name` varchar(128) DEFAULT NULL COMMENT '用户名称',
  `params` text COMMENT '参数',
  `ip` varchar(20) DEFAULT NULL COMMENT 'ip',
  `success` int DEFAULT NULL COMMENT '接口是否请求成功 0 否  1是 默认值1',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_privilege` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT 'id',
  `target_id` bigint NOT NULL COMMENT '配置id',
  `user_id` bigint DEFAULT NULL COMMENT '用户id,-1代表所有人',
  `biz_type` int DEFAULT NULL,
  `permission` int NOT NULL COMMENT '0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限',
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否删除 -1 删除  1 正常 默认值1（原 is_del）',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` varchar(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_role` (
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '逻辑删除 是否删除 1是 0 否（原 is_dtl）',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` varchar(64) NOT NULL COMMENT '更新人（原 update_by）',
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `role_id` bigint NOT NULL COMMENT '角色id',
  `user_id` bigint NOT NULL COMMENT '用户id',
  `status` int DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_security_question` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键编号',
  `user_id` bigint DEFAULT NULL COMMENT '用户编号',
  `question` varchar(500) DEFAULT NULL COMMENT '问题',
  `answer` varchar(500) DEFAULT NULL COMMENT '答案',
  `created_at` datetime(3) NOT NULL COMMENT '创建时间（原 gmt_create）',
  `updated_at` datetime(3) NOT NULL COMMENT '更新时间（原 gmt_modified）',
  `created_by` varchar(64) NOT NULL COMMENT '创建人（原 create_by）',
  `updated_by` varchar(64) NOT NULL COMMENT '更新人（原 update_by）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

