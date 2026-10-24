package com.gientech.ragcommon.graph.request;

import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import com.gientech.ragcommon.graph.dto.NodeDataDTO;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.*;

import java.io.Serializable;
import java.util.List;

/**
 * @Descrption: 节点度展开入参对象
 * @Author:liutaiyun
 * @Date:2023/02/14 16:34
 **/
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(name = "拓展查询请求参数")
public class NodeStepSearchRequest implements Serializable {

    @JsonSerialize(using = ToStringSerializer.class)
    @NotNull(message = "图谱不能为空")
    @Schema(name = "spaceName",description = "图空间")
    private String spaceName;

    @Schema(name = "fileId",description = "文件id")
    private Long fileId;

    @NotEmpty(message = "nodes不能为空")
    @Schema(name = "nodes",description = "节点")
    private List<NodeDataDTO> nodes;

    @Schema(name = "step",description = "度数 默认值1")
    private Integer step = 1;
}
