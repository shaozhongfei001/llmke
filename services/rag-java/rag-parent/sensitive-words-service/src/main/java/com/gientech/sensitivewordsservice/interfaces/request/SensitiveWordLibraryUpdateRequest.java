package com.gientech.sensitivewordsservice.interfaces.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotEmpty;
import lombok.Data;

import java.util.LinkedHashSet;


@Schema(name = "敏感词库修改请求体")
@Data
public class SensitiveWordLibraryUpdateRequest {


    /**
     * 敏感词库名称
     */
    @Schema(name = "name",description = "敏感词库名称", nullable = true)
    @NotEmpty(message="敏感词库名称不能为空！")
    private String name;

    /**
     * 敏感词
     */
    @Schema(name = "words",description = "敏感词库名称", nullable = true)
    LinkedHashSet<String> words;

    /**
     * 词库描述
     */
    @Schema(name = "descript",description = "敏感词库描述", nullable = true)
    private String descript;

}
