package com.gientech.ragcommon.infrastructure.emuns;

public interface MessageChannel {
    //知识库配置更新
    String KB_CONFIG_CHANGE_GROUP = "kb_config_change_group_unique_bak";
    String KB_CONFIG_CHANGE_TOPIC = "kb_config_change_topic_unique_bak";

    //知识库文件解析
    String KB_FILE_PARSE_GROUP = "kb_file_parse_group_unique_bak";
    String KB_FILE_PARSE_TOPIC = "kb_file_parse_topic_unique_bak";

    //重新向量化
    String RE_EMBEDDING_GROUP = "re_embedding_group_unique_bak";
    String RE_EMBEDDING_TOPIC = "re_embedding_topic_unique_bak";


    //知识库文件解析和抽取
    String KB_FILE_PARSE_EXTRACT_GROUP = "kb_file_parse_extract_group_unique_bak";
    String KB_FILE_PARSE_EXTRACT_TOPIC = "kb_file_parse_extract_topic_unique_bak";


    //知识库文件图解析
    String KB_FILE_PARSE_GRAPH_GROUP = "kb_file_parse_graph_group_unique_bak";
    String KB_FILE_PARSE_GRAPH_TOPIC = "kb_file_parse_graph_topic_unique_bak";


    //检索配置更新
    String SEARCH_CONFIG_CHANGE_GROUP = "search_config_change_group_unique_bak";
    String SEARCH_CONFIG_CHANGE_TOPIC = "search_config_change_topic_unique_bak";
}
