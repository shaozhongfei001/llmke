package com.gientech.ragcommon.graph.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.*;


/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2023/2/24 10:31
 */
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(name = "全图查询请求参数")
public class WholeGraphSearchRequest {

    @NotNull(message = "limit不能为空")
    @Schema(name = "limit",description = "limit默认值2000")
    private Long limit = 2000L;

    @NotBlank(message = "图谱不能为空")
    @Schema(name = "spaceName",description = "图空间")
    private String spaceName;

    @Schema(name = "fileId",description = "文件id")
    private Long fileId;
}
