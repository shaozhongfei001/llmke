package com.gientech.ragauthservice.domain.entity;
import lombok.Data;
import java.util.Date;

@Data
public class GroupPrivilege {

    private static final long serialVersionUID = 1L;

    /**
     * id
     */
    private Long id;

    /**
     * 目标id
     */
    private Long targetId;

    /**
     * 机构组id
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
     * 创建时间
     */
    private Date gmtCreate;

    /**
     * 更新时间
     */
    private Date gmtModified;

    /**
     * 创建人
     */
    private String createBy;

    /**
     * 更新人
     */
    private String updateBy;
}
