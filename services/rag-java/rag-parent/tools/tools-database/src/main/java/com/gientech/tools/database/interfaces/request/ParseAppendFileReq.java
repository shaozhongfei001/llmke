package com.gientech.tools.database.interfaces.request;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Schema(name = "追加文件解析请求参数")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ParseAppendFileReq {
    /** 文件ID数组 */
    @Schema(name = "fileIds",description = "文件ID数组")
    private List<Long> fileIds;

    /** 数据表编号 */
    @Schema(name = "tableId",description = "数据表编号")
    private Long tableId;
}
