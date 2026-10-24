package com.gientech.ragcommon.auth.dto;
import lombok.Data;

import java.util.Date;

@Data
public class GroupPrivilegeDTO {

    /**
     * id
     */
    private Long id;

    /**
     * 组名
     */
    private String groupName;

    /**
     * 配置id
     */

    private Long targetId;

    /**
     * 用户组id
     */
    private Long groupId;

    /**
     * 1:知识库;2:检索配置
     */
    private Integer bizType;

    /**
     * 0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限
     */
    private Integer permission;

    /**
     * 成员数量
     */
    private Long userCount;
}
