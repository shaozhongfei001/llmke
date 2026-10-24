package com.gientech.ragcommon.auth.request;

import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

/**
 * @author chenjuan
 * @date 2025/3/25 11:41
 */
@Data
public class GroupPrivilegeBatchReq {
    /**
     * 业务类型 1:知识库;2:检索配置
     */
    @NotNull(message = "bizType不能为空")
    private Integer bizType;

    /**
     * 机构组id
     */
    @NotNull(message = "groupIds不能为空")
    private Long groupId;

    /**
     * 检索配置id
     */
    @NotNull(message = "targetId不能为空")
    private Long targetId;

    /**
     * 0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限
     */
    @NotNull(message = "permission不能为空")
    private Integer permission;
}
