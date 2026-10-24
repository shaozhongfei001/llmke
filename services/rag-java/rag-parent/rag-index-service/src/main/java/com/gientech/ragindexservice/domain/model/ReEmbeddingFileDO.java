package com.gientech.ragindexservice.domain.model;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import javax.persistence.Table;
import java.util.Date;

/**
 *
 * @TableName re_embedding_file
 */
@TableName(value ="re_embedding_file")
@Data
public class ReEmbeddingFileDO {
    /**
     *
     */
    @TableId(value = "id")
    private Long id;

    /**
     *
     */
    @TableField(value = "task_id")
    private Long taskId;

    /**
     *
     */
    @TableField(value = "kb_id")
    private Long kbId;

    @TableField(value = "kb_name")
    private String kbName;

    /**
     *
     */
    @TableField(value = "file_id")
    private Long fileId;


    @TableField(value = "gmt_create", fill = FieldFill.INSERT)
    private Date gmtCreate;

    /**
     *
     */
    @TableField(value = "gmt_modified", fill = FieldFill.INSERT_UPDATE)
    private Date gmtModified;

    /**
     *
     */
    @TableField(value = "total_chunk_num")
    private Long totalChunkNum;

    /**
     *
     */
    @TableField(value = "processed_chunk_num")
    private Long processedChunkNum;

    /**
     *
     */
    @TableField(value = "error_chunk_num")
    private Long errorChunkNum;

    /**
     *
     */
    @TableField(value = "is_del")
    private Integer isDel;

    /**
     *
     */
    @TableField(value = "is_migrate")
    private Integer isMigrate;


    @TableField(value = "status")
    private Integer status;

    @TableField(value = "last_error")
    private String lastError;

}