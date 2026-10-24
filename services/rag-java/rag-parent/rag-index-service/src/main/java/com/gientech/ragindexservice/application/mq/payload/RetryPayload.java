package com.gientech.ragindexservice.application.mq.payload;

import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * @author: shirleychen
 * @date 2025/12/1 18:20
 * @description
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
public class RetryPayload {
    private Long taskId;
    private Integer type;
    private ModelSimpDTO embeddingModelInfo;
    private Long fileId;
    private String collectionName;
    private String kbName;
    private Long kbId;
    private Long taskFileId;
}
