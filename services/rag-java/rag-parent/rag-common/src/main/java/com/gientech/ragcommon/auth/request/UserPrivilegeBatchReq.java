package com.gientech.ragcommon.auth.request;

import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

@Data
public class UserPrivilegeBatchReq {

    /**
     * 业务类型 1:知识库;2:检索配置;3:模型;4:知识库文件
     */
    @NotNull(message = "bizType不能为空")
    private Integer bizType;

    /**
     * 业务目标数据id
     */
    @NotNull(message = "targetId不能为空")
    private Long targetId;

    /**
     * 用户id
     */
    @NotNull(message = "userIds不能为空")
    private Long userId;

    /**
     * 0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限
     */
    @NotNull(message = "permission不能为空")
    private Integer permission;
}
