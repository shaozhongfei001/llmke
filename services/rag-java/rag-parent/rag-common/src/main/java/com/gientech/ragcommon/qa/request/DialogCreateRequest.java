package com.gientech.ragcommon.qa.request;


import com.gientech.ragcommon.qa.enmus.SysTypeEnums;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

/**
 * @Descrption: 对话创建请求入参对象
 * @Author:liutaiyun
 * @Date:2024/05/13 09:38
 **/
@Schema(name = "对话创建请求入参对象",requiredProperties = {"label","sessionId"})
@Data
public class DialogCreateRequest {

    @Schema(name = "label",description = "对话名称")
    @NotBlank(message = "label不能为空")
    private String label;

    @Schema(name = "sessionId",description = "对话id")
    @NotBlank(message = "sessionId不能为空")
    private String sessionId;

    @Schema(name = "sysType",description = "系统类型(INT_SESSION:智能会话;KNO_INDEX:知识索引;TEMPORARY:临时会话)")
    private SysTypeEnums sysType = SysTypeEnums.KNO_INDEX;

    @Schema(name = "configId",description = "助手id")
    //@NotBlank(message = "configId不能为空")
    private Long configId;

    @Schema(name = "kbId",description = "知识id(仅用于文档上传问答使用)")
    private Long kbId;
}
