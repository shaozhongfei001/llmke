package com.gientech.sensitivewordsservice.interfaces.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import lombok.Data;

import java.util.LinkedHashSet;


@Schema(name = "敏感词库创建请求体")
@Data
public class SensitiveWordLibraryCreateRequest {


    /**
     * 敏感词库名称
     */
    @Schema(name = "name",description = "敏感词库名称", nullable = true)
    @NotBlank(message="敏感词库名称不能为空！")
    private String name;

    /**
     * 敏感词
     */
    @Schema(name = "words",description = "敏感词库名称", nullable = true)
//    @NotEmpty(message="敏感词称不能为空！")
    LinkedHashSet<String> words;

    /**
     * 词库描述
     */
    @Schema(name = "descript",description = "敏感词库描述", nullable = true)
//    @NotBlank(message="敏感词库描述不能为空！")
    private String descript;

}
