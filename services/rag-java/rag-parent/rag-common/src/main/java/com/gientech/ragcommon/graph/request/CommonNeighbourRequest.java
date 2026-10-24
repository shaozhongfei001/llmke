package com.gientech.ragcommon.graph.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;
@Schema(name = "邻居查询请求参数")
@Data
public class CommonNeighbourRequest {

    @NotNull(message = "图谱不能为空")
    @Schema(name = "spaceName",description = "图空间")
    private String spaceName;

    @NotNull(message = "节点1类型不能为空")
    @Schema(name = "nodeType1",description = "节点1类型")
    private String nodeType1;

    @NotNull(message = "节点1主键值类型不能为空")
    @Schema(name = "nodeInstanceId1",description = "节点1主键值")
    private String nodeInstanceId1;

    @NotNull(message = "节点2类型不能为空")
    @Schema(name = "nodeType2",description = "节点2类型")
    private String nodeType2;

    @NotNull(message = "节点2主键值类型不能为空")
    @Schema(name = "nodeInstanceId2",description = "节点2主键值")
    private String nodeInstanceId2;

    @Schema(name = "nodeSearchRequests",description = "节点检索条件")
    private List<NodeSearchRequest> nodeSearchRequests;

    @Schema(name = "edgeTypes",description = "边类型过滤条件")
    private List<String> edgeTypes;
}
