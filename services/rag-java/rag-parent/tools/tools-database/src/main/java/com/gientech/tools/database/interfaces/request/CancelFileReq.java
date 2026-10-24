package com.gientech.tools.database.interfaces.request;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

@Schema(name = "取消文件上传")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CancelFileReq {
    /** 文件ID数组 */
    @Schema(name = "fileIds",description = "文件ID数组")
    private List<Long> fileIds;
}
