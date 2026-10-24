package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import java.math.BigDecimal;
import java.util.Date;

@Schema(name = "保存请求参数")
@Data
public class SaveFileParseTaskReq {

    @Schema(name = "kbId",description = "知识库id")
    private Long kbId;

    @Schema(name = "kbName",description = "知识库名称")
    private String kbName;

    @Schema(name = "fileId",description = "文件id")
    private Long fileId;

    @Schema(name = "fileName",description = "文件库名称")
    private String fileName;

    @Schema(name = "taskInfo",description = "任务详情")
    private String taskInfo;

    @Schema(name = "status",description = "状态 -1:删除 1:待处理 2:处理中,3:重试中 4: 成功 5: 处理失败")
    private Integer status;

    @Schema(name = "startTime",description = "解析开始时间")
    private Date startTime;

    @Schema(name = "endTime",description = "解析结束时间")
    private Date endTime;

    @Schema(name = "retryLimit",description = "重试限制次数")
    private Integer retryLimit;

    @Schema(name = "retryTimes",description = "已经重试次数")
    private Integer retryTimes;

    @Schema(name = "errorMsg",description = "失败原因")
    private String errorMsg;

    @Schema(name = "modifyBy",description = "修改人")
    private String modifyBy;

}
