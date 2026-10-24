package com.gientech.ragcommon.index.enmus;

import java.util.Arrays;
import java.util.List;

public interface FileFieldEnums {

    List<String> FILE_TYPE_LIST = Arrays.asList("xlsx","xls","csv");

    /**
     * 仅用于faq抽取的知识库
     */
    String FAQ_EXTRACT_CHUNK_PREFIX = "chunks_faq_";

    String TABLE_SUMMARY_PREFIX = "table_summary_";

    String TABLE_CHUNKS_PREFIX = "table_chunks_";

    String FAQ_TABLE_NAME_PREFIX = "faq_";

    /**
     * 图片
     */
    String IMAGES = "images";

    /**
     * 文本
     */
    String TEXTS = "texts";

    /**
     * 图
     */
    //图实体信息
    String GRAPH_ENTITY_PREFIX = "graph_entity_";

    //删除milvus图实体所需要的固定字段
    String GRAPH_BASE = "graph_base";

    String FILE_SEPARATOR = "/";

}
