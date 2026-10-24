package com.gientech.ragcommon.graph.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.*;

import java.io.Serializable;
import java.util.List;

/**
 * @Descrption: 边查询入参对象
 * @Author:liutaiyun
 * @Date:2023/02/14 16:07
 **/
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(name = "边查询请求参数")
public class EdgeSearchRequest implements Serializable {

    @NotBlank(message = "spaceName不能为空")
    @Schema(name = "spaceName",description = "图空间")
    private String spaceName;

    @Schema(name = "fileId",description = "文件id")
    private Long fileId;

    @NotBlank(message = "边类型不能为空")
    @Schema(name = "edgeType",description = "边类型")
    private String edgeType;

    @Schema(name = "edgePropertiesConditions",description = "边属性条件")
    private List<SearchConditionRequest> edgePropertiesConditions;

    @Schema(name = "fromNodeSearchRequest",description = "头节点查询条件")
    private NodeSearchRequest fromNodeSearchRequest;

    @Schema(name = "tailNodeSearchRequest",description = "尾节点查询条件")
    private NodeSearchRequest tailNodeSearchRequest;
}
