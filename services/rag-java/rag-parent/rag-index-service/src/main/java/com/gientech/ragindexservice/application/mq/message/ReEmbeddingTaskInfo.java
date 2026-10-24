package com.gientech.ragindexservice.application.mq.message;

import com.alibaba.fastjson2.JSON;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import com.gientech.ragcommon.infrastructure.emuns.MessageChannel;
import com.gientech.ragindexservice.domain.model.ReEmbeddingTaskDO;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.apache.rocketmq.common.message.Message;

/**
 * @author: shirleychen
 * @date 2025/11/20 17:55
 * @description
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
public class ReEmbeddingTaskInfo{
    private Long id;
    private Long kbId;
    private String knowledgeBaseName;
    private ModelSimpDTO embeddingModelInfo;

    public ReEmbeddingTaskInfo(Long kbId, String knowledgeBaseName, ModelSimpDTO embeddingModelInfo) {
        this.kbId = kbId;
        this.knowledgeBaseName = knowledgeBaseName;
        this.embeddingModelInfo = embeddingModelInfo;
    }

    public static Message buildReEmbeddingMessage(Long id, Long kbId, String kbName, ModelSimpDTO embeddingModelInfo) {
        Message message = new Message();
        message.setBody(JSON.toJSONBytes(new ReEmbeddingTaskInfo(id, kbId, kbName, embeddingModelInfo)));
        message.setTopic(MessageChannel.RE_EMBEDDING_TOPIC);
        return message;
    }

    public static ReEmbeddingTaskDO buildReEmbeddingTaskDO(ReEmbeddingTaskInfo reEmbeddingTaskInfo) {
        ReEmbeddingTaskDO taskDO = new ReEmbeddingTaskDO();

        taskDO.setKbId(reEmbeddingTaskInfo.getKbId());
        taskDO.setKbName(reEmbeddingTaskInfo.getKnowledgeBaseName());
        taskDO.setStatus(1);
        return taskDO;
    }

    public String getNewMilvusCollectionName() {
        return knowledgeBaseName + "_" + id;
    }
}
