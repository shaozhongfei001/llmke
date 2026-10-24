package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(name = "山粗文本块请求参数")
@Data
public class DeleteChunkReq {

    @NotNull(message = "tableName不能为空")
    @Schema(name = "tableName",description = "tableName")
    private String tableName;

    @NotEmpty(message = "文本块id不能为空")
    @Schema(name = "chunkIds",description = "文本块id")
    private List<String> chunkIds;

}
