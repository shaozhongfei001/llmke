package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(name = "文本chunk关联图片chunk调整请求参数")
@Data
public class ChunkChangeReq {

    @NotNull(message = "fileId不能为空")
    @Schema(name = "fileId",description = "文件id")
    private Long fileId;

    @NotNull(message = "oldChunkId不能为空")
    @Schema(name = "oldChunkId",description = "原来的文本chunkId")
    private Long oldChunkId;

    @NotNull(message = "newChunkId不能为空")
    @Schema(name = "newChunkId",description = "新的文本chunkId")
    private Long newChunkId;

    @NotNull(message = "imageChunkId不能为空")
    @Schema(name = "imageChunkId",description = "需要调整的图片的chunkId")
    private Long imageChunkId;
}
