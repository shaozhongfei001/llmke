package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Schema(name = "图解析请求参数体", requiredProperties = {"kbId", "fileIds"})
@Data
@AllArgsConstructor
@NoArgsConstructor
public class GraphParseReq {

    @NotNull
    @Schema(name = "kbId", description = "知识库库id")
    private Long kbId;

    @NotEmpty
    @Schema(name = "fileIds", description = "知识库文件id")
    private List<Long> fileIds;

    @Schema(name = "reParse", description = "是否重新解析 true 是；false 否 默认false")
    private Boolean reParse = false;
}
