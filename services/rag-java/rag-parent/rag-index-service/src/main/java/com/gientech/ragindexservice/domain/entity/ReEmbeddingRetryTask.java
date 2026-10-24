package com.gientech.ragindexservice.domain.entity;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Date;
import java.util.concurrent.CompletableFuture;

/**
 * @author: shirleychen
 * @date 2025/12/2 10:23
 * @description
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
public class ReEmbeddingRetryTask {
    private Long taskId;
    private Long retryTaskId;
    private Runnable runnable;
    private CompletableFuture<Void> future;
    private int retryTimes;
    private Date gmtCreate;
    private String kbName;
    private String collectionName;
    private Long fileId;
    private Integer type;

}
