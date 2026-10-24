package com.gientech.ragindexservice.application.mq.payload;

import com.gientech.ragcommon.auth.dto.UserInfoDTO;
import com.gientech.ragcommon.index.dto.KnowledgeBaseFileDTO;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * @author: shirleychen
 * @date 2025/12/4 14:17
 * @description
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
public class ReParseFilePayload extends RetryPayload {
    private KnowledgeBaseFileDTO file;
    private String userName;
    private String userId;
    private boolean retry;

    public ReParseFilePayload(Long taskId, Integer type, ModelSimpDTO embeddingModelInfo, Long fileId, String collectionName, String kbName, Long kbId, KnowledgeBaseFileDTO file, UserInfoDTO user, Long taskFileId) {
        super(taskId, type, embeddingModelInfo, fileId, collectionName, kbName, kbId, taskFileId);
        this.file = file;
        this.userName = user.getUserName();
        this.userId = String.valueOf(user.getId());
    }
}
