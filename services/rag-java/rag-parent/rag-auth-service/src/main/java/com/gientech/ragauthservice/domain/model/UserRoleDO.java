package com.gientech.ragauthservice.domain.model;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.gitee.sunchenbin.mybatis.actable.annotation.*;
import com.gitee.sunchenbin.mybatis.actable.constants.MySqlTypeConstant;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.io.Serializable;
import java.util.Date;

@Builder
@Data
@NoArgsConstructor
@AllArgsConstructor
@TableName("user_role")
@TableComment("用户-角色关系表")
public class UserRoleDO implements Serializable {

    private static final long serialVersionUID = 1L;

    @Column(name = "is_dtl", defaultValue = "0", comment = "逻辑删除 是否删除 1是 0 否")
    private String isDtl;

    @Column(name = "gmt_create", comment = "创建时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtCreate;

    @Column(name = "gmt_modified", comment = "更新时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtModified;

    @Column(name = "create_by", comment = "创建人", length = 128)
    private String createBy;

    @Column(name = "update_by", comment = "更新人", length = 128)
    private String updateBy;

    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", isNull = false, comment = "主键" ,isKey = true ,isAutoIncrement = true)
    private Long id;

    @Column(name = "role_id", isNull = false, comment = "角色id")
    private Long roleId;

    @Column(name = "user_id", isNull = false, comment = "用户id")
    private Long userId;

    @Column(name = "status", defaultValue = "1", comment = "状态(1:启用; 0:禁用)")
    private Integer status;

}
