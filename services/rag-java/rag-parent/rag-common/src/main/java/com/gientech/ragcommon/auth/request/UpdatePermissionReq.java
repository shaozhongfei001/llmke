package com.gientech.ragcommon.auth.request;

import com.gientech.ragcommon.auth.enums.FrameElementTypeEnums;
import com.gientech.ragcommon.auth.enums.PrivilegeTypeEnums;
import com.gientech.ragcommon.index.enmus.PermissionEnums;
import lombok.Data;

import java.security.Permission;

/**
 * @author chenjuan
 * @date 2025/3/28 16:51
 */
@Data
public class UpdatePermissionReq {
    private Long targetId;

    private PrivilegeTypeEnums bizType = PrivilegeTypeEnums.KNOWLEDGE_BASE;

    private FrameElementTypeEnums elementType;

    private Long elementId;

    private PermissionEnums currentPermission;

    private PermissionEnums targetPermission;
}
