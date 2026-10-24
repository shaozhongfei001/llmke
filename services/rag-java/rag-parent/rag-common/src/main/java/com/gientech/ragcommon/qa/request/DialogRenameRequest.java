package com.gientech.ragcommon.qa.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

/**
 * @Descrption: 对话重命名请求入参对象
 * @Author:liutaiyun
 * @Date:2024/05/13 15:25
 **/
@Schema(name = "对话重命名请求入参对象",requiredProperties = {"id","name"})
@Data
public class DialogRenameRequest {

    @Schema(name = "sessionId",description = "对话id")
    @NotBlank(message = "sessionId不能为空")
    private String sessionId;

    @Schema(name = "label",description = "对话名称(新的)")
    @NotBlank(message = "label不能为空")
    private String label;

}
