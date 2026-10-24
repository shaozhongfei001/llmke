package com.gientech.ragindexservice.application.mq.payload;

import com.gientech.ragcommon.index.dto.KnowledgeBaseFileDTO;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;

/**
 * @author: shirleychen
 * @date 2025/12/1 15:57
 * @description
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
@Slf4j
public class ProcessFilePayload extends RetryPayload {
    private KnowledgeBaseFileDTO file;
    private boolean retry;

    public ProcessFilePayload(KnowledgeBaseFileDTO file, ModelSimpDTO embeddingModelInfo, Integer type, Long taskId, Long fileId, String collectionName, String kbName, Long kbId, Long taskFileId) {
        super(taskId, type, embeddingModelInfo, fileId, collectionName, kbName, kbId, taskFileId);
        this.file = file;
    }

    public ProcessFilePayload(RetryPayload payload, KnowledgeBaseFileDTO file) {
        super(payload.getTaskId(), payload.getType(), payload.getEmbeddingModelInfo(), payload.getFileId(), payload.getCollectionName(), payload.getKbName(), payload.getKbId(), payload.getTaskFileId());
        this.file = file;
    }

}
