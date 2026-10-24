package com.gientech.ragcommon.graph.request;

import com.gientech.ragcommon.graph.dto.NodeDataDTO;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.NotNull;
import lombok.*;
import java.util.List;

/**
 * @Descrption: 路径查询入参对象
 * @Author:liutaiyun
 * @Date:2023/02/14 16:20
 **/
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(name = "路径查询请求参数")
public class PathSearchRequest {

    @NotNull(message = "图谱不能为空")
    @Schema(name = "spaceName",description = "图空间")
    private String spaceName;

    @Schema(name = "fromNode",description = "头节点")
    private NodeDataDTO fromNode;

    @Schema(name = "tailNode",description = "未节点")
    private NodeDataDTO tailNode;

    @NotNull
    @Schema(name = "direction",description = "边的方向（相对于第一个节点），取值是：1 出度，2 入度,3 双向bidirect")
    private Integer direction;

    @Schema(name = "step",description = "最大步数为5")
    @Max(value = 5, message = "最大步数为5")
    private Integer step = 1;

    @NotNull
    @Schema(name = "searchType",description = "查询类型，取值是：全路径1 all，最短路径 2 shortest，非循环路径 3 noloop")
    private Integer searchType;

    @Schema(name = "edgeTypes",description = "边类型列表 非必填 默认为*")
    private List<String> edgeTypes;

    @Schema(name = "nodeTypes",description = "点类型列表 非必填 默认为*")
    private List<String> nodeTypes;

    @Schema(name = "conditions",description = "边查询条件")
    private List<EdgeSearchRequest> conditions;

}
