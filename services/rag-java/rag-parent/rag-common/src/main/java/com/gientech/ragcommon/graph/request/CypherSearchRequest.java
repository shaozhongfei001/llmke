package com.gientech.ragcommon.graph.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.*;

import java.io.Serializable;

/**
 * @Descrption: cypher查询入参对象
 * @Author:liutaiyun
 * @Date:2023/02/14 16:16
 **/
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(name = "cypher语句查询请求参数")
public class CypherSearchRequest implements Serializable {

    @NotNull(message = "图谱不能为空")
    @Schema(name = "spaceName",description = "图空间")
    private String spaceName;

    @Schema(name = "fileId",description = "文件id")
    private Long fileId;

    @NotNull(message = "cypher语句不能为空")
    @Schema(name = "cypher",description = "cypher语句")
    private String cypher;
}
