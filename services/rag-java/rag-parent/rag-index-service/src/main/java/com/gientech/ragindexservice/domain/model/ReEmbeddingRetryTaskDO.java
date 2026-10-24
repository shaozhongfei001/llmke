package com.gientech.ragindexservice.domain.model;

import com.baomidou.mybatisplus.annotation.*;

import java.util.Date;
import lombok.Data;

/**
 * 
 * @TableName re_embedding_retry_task
 */
@TableName(value ="re_embedding_retry_task")
@Data
public class ReEmbeddingRetryTaskDO {
    /**
     * 
     */
    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    /**
     * 
     */
    @TableField(value = "uid")
    private String uid;

    /**
     * 
     */
    @TableField(value = "task_id")
    private Long taskId;

    /**
     * 1-file 2-chunk
     */
    @TableField(value = "type")
    private Integer type;

    /**
     * 
     */
    @TableField(value = "payload")
    private String payload;

    /**
     * 任务重试简要概括
     */
    @TableField(value = "last_error")
    private String lastError;

    /**
     * 
     */
    @TableField(value = "gmt_create", fill = FieldFill.INSERT)
    private Date gmtCreate;

    /**
     * 
     */
    @TableField(value = "gmt_modified", fill = FieldFill.INSERT_UPDATE)
    private Date gmtModified;

    /**
     * 重试次数
     */
    @TableField(value = "retry_times")
    private int retryTimes;


    @TableField(value = "is_del")
    private int isDel;

    /**
     * 1-处理中 2-等待处理 3-处理完成 4-处理失败
     */
    @TableField(value = "status")
    private Integer status;


    @TableField(value = "file_id")
    private Long fileId;

    @TableField(value = "kb_id")
    private Long kbId;
}