package com.gientech.ragindexservice.application.remote.request;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * @author: shirleychen
 * @date 2025/12/5 14:28
 * {
 * "db_name": "rag_knowledge_base",
 * "origin_collection": "collection_new",
 * "target_collection": "collection",
 * "filter": {
 * "file_id": { "_in": ["f001", "f002", "f003"] }   // 以文件粒度迁移
 * },
 * "batch_size": 2000         // 迁移分批执行
 * }
 * @description
 */
@Data
public class PyMigrateRequest {
    @JsonProperty("db_name")
    private String dbName = "rag_knowledge_base";
    @JsonProperty("origin_collection")
    private String originCollection;
    @JsonProperty("target_collection")
    private String targetCollection;
    @JsonProperty("filter")
    private Filter filter;
    @JsonProperty("batch_size")
    private Integer batchSize;

    @Data
    public static class Filter {
        @JsonProperty("file_id")
        private FileIdCondition fileId;

        public Filter(Long fileId) {
            this.fileId = new FileIdCondition(List.of(String.valueOf(fileId)));
        }
    }

    @Data
    @AllArgsConstructor
    public static class FileIdCondition {
        @JsonProperty("_in")
        private List<String> in;
    }


    public PyMigrateRequest(String originCollection, String targetCollection, Long fileId, Integer batchSize) {
        this.originCollection = originCollection;
        this.targetCollection = targetCollection;
        this.filter = new Filter(fileId);
        this.batchSize = batchSize;
    }
}
