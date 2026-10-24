package com.gientech.ragindexservice.domain.model;

/**
 * @author: shirleychen
 * @date 2025/11/25 15:57
 * @description
 */

import com.baomidou.mybatisplus.annotation.*;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragindexservice.application.mq.message.ReEmbeddingTaskInfo;
import com.gitee.sunchenbin.mybatis.actable.annotation.Column;
import com.gitee.sunchenbin.mybatis.actable.constants.MySqlTypeConstant;
import lombok.Data;

import java.util.Date;

/**
 * @TableName re_embedding_task
 */
@TableName(value = "re_embedding_task")
@Data
public class ReEmbeddingTaskDO {
    /**
     *
     */
    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    /**
     * 知识库id
     */
    @TableField(value = "kb_id")
    private Long kbId;

    /**
     * 知识库名称
     */
    @TableField(value = "kb_name")
    private String kbName;

    /**
     * 重新向量化使用的模型
     */
    @TableField(value = "embedding_model_name")
    private String embeddingModelName;

    /**
     * 1-解析中 2-解析完成 9-解析失败
     */
    @TableField(value = "status")
    private Integer status;

    /**
     * 1-删了 0-没删
     */
    @TableField(value = "is_del")
    private Integer isDel;

    /**
     * 概要日志
     */
    @TableField(value = "log_summary")
    private String logSummary;


    @Column(name = "gmt_create", comment = "创建时间", type = MySqlTypeConstant.DATETIME)
    @TableField(fill = FieldFill.INSERT)
    private Date gmtCreate;


    @Column(name = "gmt_modified", comment = "更新时间", type = MySqlTypeConstant.DATETIME)
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private Date gmtModified;

    @TableField(value = "msg_key")
    private String msgKey;

    @TableField(value = "total_file_num")
    private Long totalFileNum;

    @TableField(value = "uid")
    private String uid;

    @TableField(value = "create_by")
    private String createBy;

    @TableField(value = "modified_by")
    private String modifiedBy;


    public static ReEmbeddingTaskDO buildReEmbeddingTask(ReEmbeddingTaskInfo reEmbeddingTaskInfo) {
        ReEmbeddingTaskDO reEmbeddingTask = new ReEmbeddingTaskDO();
        reEmbeddingTask.setKbId(reEmbeddingTaskInfo.getKbId());
        reEmbeddingTask.setKbName(reEmbeddingTaskInfo.getKnowledgeBaseName());
        reEmbeddingTask.setEmbeddingModelName(reEmbeddingTaskInfo.getEmbeddingModelInfo().getModelName());
        return reEmbeddingTask;
    }

    public static ReEmbeddingTaskDO buildReEmbeddingTask(String uid, Long kbId, String kbName, String embeddingModelName) {
        ReEmbeddingTaskDO reEmbeddingTask = new ReEmbeddingTaskDO();
        reEmbeddingTask.setUid(uid);
        reEmbeddingTask.setKbId(kbId);
        reEmbeddingTask.setKbName(kbName);
        reEmbeddingTask.setEmbeddingModelName(embeddingModelName);
        reEmbeddingTask.setCreateBy(UserContext.getUser().getUserName());
        reEmbeddingTask.setModifiedBy(UserContext.getUser().getUserName());
        return reEmbeddingTask;
    }

}
