package com.gientech.ragindexservice.domain.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.math.BigDecimal;
import java.util.Date;
import java.util.LinkedHashSet;

@AllArgsConstructor
@NoArgsConstructor
@Data
public class FileParseTask {

    private static final long serialVersionUID = 1L;

    /**
     * 主键
    */
    private Long id;

    /**
     * 知识库id
    */
    private Long kbId;

    /**
     * 知识库名称
    */
    private String kbName;

    /**
     * 文件id
    */
    private Long fileId;

    /**
     * 文件库名称
    */
    private String fileName;

    /**
     * 任务详情
    */
    private String taskInfo;

    /**
     * 状态 -1:删除 1:待处理 2:处理中,3:重试中 4: 成功 5: 处理失败
    */
    private Integer status;

    /**
     * 解析开始时间
    */
    private Date startTime;

    /**
     * 解析结束时间
    */
    private Date endTime;

    /**
     * 重试限制次数
    */
    private Integer retryLimit;

    /**
     * 已经重试次数
    */
    private Integer retryTimes;

    /**
     * 失败原因
    */
    private String errorMsg;

    /**
     * 创建人
    */
    private String createBy;

    /**
     * 创建时间
    */
    private Date gmtCreate;

    /**
     * 修改人
    */
    private String modifyBy;

    /**
     * 修改时间
    */
    private Date gmtModified;

}
