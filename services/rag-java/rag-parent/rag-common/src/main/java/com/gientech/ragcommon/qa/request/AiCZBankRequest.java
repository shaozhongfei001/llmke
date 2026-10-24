package com.gientech.ragcommon.qa.request;


import com.gientech.ragcommon.qa.enmus.SysTypeEnums;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.Date;

/**
 * @Description:
 * @Author: ws
 * @Date: 2024/6/3 11:17
 */
@Schema(name = "AI请求体(浙商)")
@Data
public class AiCZBankRequest {

    @Schema(name = "content",description = "提问内容", nullable = true)
    @NotBlank(message="提问内容不能为空！")
    private String content;

    @Schema(name = "configId",description = "检索配置id", nullable = true)
    private Long configId;

}
