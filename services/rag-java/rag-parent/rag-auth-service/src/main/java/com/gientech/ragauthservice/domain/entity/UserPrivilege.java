package com.gientech.ragauthservice.domain.entity;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.Date;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserPrivilege implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * id
     */
    private Long id;

    /**
     * 配置id
     */
    private Long targetId;

    private List<Long> targetIds;

    /**
     * 用户id,-1代表所有人
     */
    private Long userId;

    /**
     * 1:知识库;2:检索配置;3:模型
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
