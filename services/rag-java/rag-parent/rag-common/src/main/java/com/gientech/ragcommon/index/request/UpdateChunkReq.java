package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(name = "更新文本块请求参数")
@Data
public class UpdateChunkReq {

    @NotNull(message = "知识库id不能为空")
    @Schema(name = "KbId",description = "知识库id")
    private Long kbId;

    @NotBlank(message = "文本块id不能为空")
    @Schema(name = "chunkId",description = "文本块id")
    private String chunkId;

    @NotBlank(message = "文本块内容不能为空")
    @Schema(name = "content",description = "文本块内容")
    private String content;

}
