# 服务启动配置
from urllib import parse

retrieval_results_schema = """
    create table generate_retrieval_results
    (
        id int,
        external_pk varchar(100) default null comment '外建id',
        question varchar(255) default null  comment '当前问题',
        original_question varchar(255) default null  comment '初始问题',
        knowledge_base_name varchar(255) default null comment '知识库名称',
        page_content text default null comment '查询结果',
        search_source varchar(100) default null  comment '召回来源',
        source_rank int default  null  comment '排序',
        top_k int default  null  comment '召回数量',
        offset text default null comment 'chunk位置',
        rrf_scores float default  null  comment 'rrf的分数',
        query_weight float default null  comment '查询权重',
        faq_answer text default  null  comment 'faq答案',
        faq_filter_threshold float default  null  comment 'faq筛选最小分数',
        rerank_model varchar(100) default null  comment 'rerank_model_name',
        rerank_filter_threshold float default null  comment 'rerank筛选最小分数',
        rerank_score float default null   comment 'rerank最后得分',
        create_time TIMESTAMP default CURRENT_TIMESTAMP   comment 'log创建时间'
    )
    comment '检索日志记录';

create unique index generate_retrieval_results_id_uindex
    on generate_retrieval_results (id);

alter table generate_retrieval_results
    add constraint generate_retrieval_results_pk
        primary key (id);

alter table generate_retrieval_results modify id int auto_increment;
"""

llm_results_schema = """
    create table generate_llm_results
    (
        id int,
        external_pk varchar(100) default null comment '外建id',
        question varchar(255) default null  comment '当前问题',
        original_question varchar(255) default null  comment '初始问题',
        knowledge_base_name varchar(255) default null comment '知识库名称',
        model_name varchar(255) default null comment '推理模型名称',
        documents text default null comment '提供文本',
        llm_results text default null comment '查询结果',
        temperature varchar(100) default null  comment '温度',
        max_tokens int default  null  comment '最大tokens',
        top_k int default  null  comment '返回数量',
        prompt_text text default null comment 'prompt',
        chat_history text default null comment '历史信息',
        create_time TIMESTAMP default CURRENT_TIMESTAMP   comment 'log创建时间'
    )
    comment '检索日志记录';

create unique index generate_llm_results_id_uindex
    on generate_llm_results (id);

alter table generate_llm_results
    add constraint generate_llm_results_pk
        primary key (id);

alter table generate_llm_results modify id int auto_increment;
"""
