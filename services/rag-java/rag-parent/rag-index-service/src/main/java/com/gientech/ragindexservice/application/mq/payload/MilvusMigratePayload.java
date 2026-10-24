package com.gientech.ragindexservice.application.mq.payload;

import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * @author: shirleychen
 * @date 2025/12/5 14:44
 * @description
 */
@Data
@NoArgsConstructor
public class MilvusMigratePayload extends RetryPayload {
    private Integer batchSize;
    private String sourceCollection;
    private String targetCollection;

    public MilvusMigratePayload(Long taskId, Integer type, ModelSimpDTO embeddingModelInfo, Long fileId, String collectionName, String kbName, Long kbId, Integer batchSize, Long taskFileId) {
        super(taskId, type, embeddingModelInfo, fileId, collectionName, kbName, kbId, taskFileId);
        this.batchSize = batchSize;
        this.sourceCollection = collectionName;
        this.targetCollection = kbName;
    }

}
