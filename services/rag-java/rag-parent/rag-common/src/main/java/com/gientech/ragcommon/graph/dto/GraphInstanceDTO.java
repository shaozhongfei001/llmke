package com.gientech.ragcommon.graph.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Schema(name = "图的点和边的实例数")
@Data
public class GraphInstanceDTO {

    @Schema(name = "fileId",description = "文件id")
    private Long fileId;

    @Schema(name = "nodeCount",description = "节点实例数")
    private  Integer nodeCount;

    @Schema(name = "edgeCount",description = "边实例数")
    private Integer edgeCount;
}
