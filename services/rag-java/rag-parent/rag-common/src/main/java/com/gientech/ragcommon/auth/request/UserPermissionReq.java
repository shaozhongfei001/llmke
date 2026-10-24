package com.gientech.ragcommon.auth.request;

import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class UserPermissionReq {

    /**
     * 用户id
     */
    @NotNull(message = "guserId不能为空")
    private Long userId;

    /**
     * 1:知识库;2:检索配置;3:模型
     */
    @NotNull(message = "bizType不能为空")
    private Integer bizType;

    /**
     * 0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限
     */
    @NotNull(message = "permission不能为空")
    private Integer permission;

    /**
     * 目标数据id
     */
    @NotNull(message = "targetId不能为空")
    private Long targetId;

    private boolean withUser;
}
