package com.gientech.ragcommon.auth.request;

import com.gientech.ragcommon.auth.enums.PrivilegeTypeEnums;
import com.gientech.ragcommon.auth.enums.TransferTypeEnums;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

/**
 * @author chenjuan
 * @date 2025/3/23 17:41
 */
@Data
public class TransferPropertyReq {
    @NotNull(message = "transferType 不能为空")
    private TransferTypeEnums transferType;

    private List<TransferPropertyElement> transferProperties;

    @Data
    public static class TransferPropertyElement {
        private Long userId;

        @NotNull(message = "userId 不能为空")
        private Long targetUserId;

        @NotNull(message = "type 不能为空")
        private PrivilegeTypeEnums type;
    }
}
