package com.gientech.ragcommon.graph.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.List;

/**
 * @Descrption: 节点查询入参对象
 * @Author:liutaiyun
 * @Date:2023/02/14 15:53
 **/
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(name = "点查询请求参数")
public class NodeSearchRequest implements Serializable {

    @NotBlank(message = "spaceName不能为空")
    @Schema(name = "spaceName",description = "图空间")
    private String spaceName;

    @Schema(name = "fileId",description = "文件id")
    private Long fileId;

    @NotBlank(message = "节点类型不能为空")
    @Schema(name = "nodeType",description = "节点类型")
    private String nodeType;

    @Schema(name = "name",description = "名称，用于模糊匹配")
    private String name;

    @Schema(name = "searchConditions",description = "查询条件（属性过滤条件）")
    private List<SearchConditionRequest> searchConditions;

}
