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
public class UpdateGroupPermissionReq {

    /**
     * 机构组id
     */
    @NotNull(message = "groupId不能为空")
    private Long groupId;

    /**
     * 目标数据id
     */
    @NotNull(message = "targetId不能为空")
    private Long targetId;

    /**
     * 1:知识库;2:检索配置
     */
    @NotNull(message = "bizType不能为空")
    private Integer bizType;

    /**
     * 0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限
     */
    @NotNull(message = "permission不能为空")
    private Integer permission;
}
