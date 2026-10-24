package com.gientech.ragcommon.qa.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Schema(name = "反馈请求参数",requiredProperties = {"queryId","restult"})
@Data
public class FeedbackReq {

    @Schema(name = "queryId",description = "queryId")
    @NotBlank(message = "queryId不能为空")
    private String queryId;

    @Schema(name = "restult",description = "0：踩；1：赞")
    @NotNull(message = "restult不能为空")
    private Integer restult;

    @Schema(name = "userRealname",description = "用户真实名称")
    private String userRealname;

    @Schema(name = "deptName",description = "部门名称")
    private String deptName;

    @Schema(name = "userPhone",description = "收集")
    private String userPhone;

    @Schema(name = "queError",description = "理解问题有误")
    private String queError;

    @Schema(name = "ansPoor",description = "回答不佳")
    private String ansPoor;

    @Schema(name = "formatError",description = "格式错误")
    private String formatError;

    @Schema(name = "harmfulInfo",description = "有害信息")
    private String harmfulInfo;

    @Schema(name = "othres",description = "其他")
    private String othres;

    @Schema(name = "supplementExplain",description = "补充说明")
    private String supplementExplain;

    @Schema(name = "idealAnswer",description = "理想回答")
    private String idealAnswer;
}
