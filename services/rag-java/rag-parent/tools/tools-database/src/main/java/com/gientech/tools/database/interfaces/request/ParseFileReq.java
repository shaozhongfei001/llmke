package com.gientech.tools.database.interfaces.request;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

@Schema(name = "文件解析请求参数")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ParseFileReq {
    /** 文件ID数组 */
    @Schema(name = "fileIds",description = "文件ID数组")
    private List<Long> fileIds;

    /** 自定义表描述:key-value结构，key为FileID */
    @Schema(name = "tableDescriptionMap",description = "自定义表描述:key-value结构，key为FileID")
    Map<Long, String> tableDescriptionMap;

    /** 是否Ai生成描述 */
    @Schema(name = "isGenDescription",description = "是否Ai生成描述")
    private Boolean isGenDescription;
}
