package com.gientech.ragcommon.index.request;

import com.gientech.ragcommon.auth.enums.BizTypeEnums;
import com.gientech.ragcommon.index.enmus.FileFieldEnums;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * @author chenjuan
 * @date 2025/5/16 17:40
 */
@Schema(name = "文件/文件夹转移请求参数")
@Data
@AllArgsConstructor
@NoArgsConstructor
public class TransferBatchReq {
    @Schema(name = "targetFolderId", description = "目标文件夹的id")
    private Long targetFolderId;

    @Schema(name = "target", description = "")
    @NotNull
    private List<TransferTarget> target;


    @Data
    public static class TransferTarget {
        private Long targetId;
        private BizTypeEnums bizType;
        private String kbName;
    }

}
