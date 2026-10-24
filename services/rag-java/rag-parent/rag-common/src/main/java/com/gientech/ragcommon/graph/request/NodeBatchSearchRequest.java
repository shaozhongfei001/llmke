package com.gientech.ragcommon.graph.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2023/3/28 17:56
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(name = "节点批量查询请求参数")
public class NodeBatchSearchRequest {

    @NotNull(message = "图谱不能为空")
    @Schema(name = "spaceName",description = "图空间")
    private String spaceName;

    @NotEmpty(message = "ids不能为空")
    @Schema(name = "ids",description = "ids不能为空")
    private List<String> ids;
}
