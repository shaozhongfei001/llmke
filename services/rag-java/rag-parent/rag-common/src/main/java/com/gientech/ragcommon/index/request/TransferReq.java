package com.gientech.ragcommon.index.request;

import com.gientech.ragcommon.auth.enums.BizTypeEnums;
import com.gientech.ragcommon.index.enmus.FileFieldEnums;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * @author chenjuan
 * @date 2025/5/16 17:40
 */
@Schema(name = "文件/文件夹转移请求参数")
@Data
@AllArgsConstructor
@NoArgsConstructor
public class TransferReq {
    @Schema(name = "targetFolderId", description = "目标文件夹的id")
    private Long targetFolderId;

    @NotNull(message = "targetId不能为空")
    @Schema(name = "targetId", description = "文件/文件夹id")
    private Long targetId;

    @Schema(name = "bizType", description = "类型")
    @NotNull
    private BizTypeEnums bizType;

    @Schema(name = "kbName", description = "知识库名称")
    @NotBlank
    private String kbName;
}
