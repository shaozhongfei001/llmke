package com.gientech.ragindexservice.application.mq.payload;

import com.gientech.ragcommon.index.FileChunkDTO;
import com.gientech.ragcommon.index.dto.FileMetadataChunkDTO;
import com.gientech.ragcommon.index.dto.KnowledgeBaseFileDTO;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;

import java.util.List;

/**
 * @author: shirleychen
 * @date 2025/12/1 16:43
 * @description
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
@Slf4j
public class ReEmbeddingChunkPayload extends RetryPayload {
    private List<FileChunkDTO> documentList;
    private Long totalChunks;
    private KnowledgeBaseFileDTO file;

    public ReEmbeddingChunkPayload(KnowledgeBaseFileDTO file, List<FileChunkDTO> documentList, ModelSimpDTO embeddingModelInfo, Integer type, Long taskId, Long fileId, String collectionName, String kbName, Long kbId, Long totalChunks, Long taskFileId) {
        super(taskId, type, embeddingModelInfo, fileId, collectionName, kbName, kbId, taskFileId);
        this.documentList = documentList;
        this.totalChunks = totalChunks;
        this.file = file;
    }
}
