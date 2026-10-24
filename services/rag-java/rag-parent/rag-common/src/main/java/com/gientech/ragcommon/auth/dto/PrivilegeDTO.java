package com.gientech.ragcommon.auth.dto;
import lombok.Data;

@Data
public class PrivilegeDTO {

    /**
     * 目标数据id
     */
    private Long targetId;

    /**
     * 1:知识库;2:检索配置;3:模型
     */
    private Integer bizType;

    /**
     * 0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限
     */
    private Integer permission;
}
