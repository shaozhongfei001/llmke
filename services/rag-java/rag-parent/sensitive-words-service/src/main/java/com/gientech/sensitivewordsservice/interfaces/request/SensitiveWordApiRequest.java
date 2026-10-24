package com.gientech.sensitivewordsservice.interfaces.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.util.List;

@Schema(name = "判断是否敏感词")
@Data
public class SensitiveWordApiRequest {

    @Schema(name = "sourceText",description = "涉敏检查原文本", nullable = true)
    @NotBlank(message="涉敏检查原文本不能为空！")
    private String sourceText;

    @Schema(name = "libraryIds",description = "指定的敏感词库id数组", nullable = true)
    private List<Long> libraryIds;
}
