package com.gientech.ragauthservice.domain.model;

import com.baomidou.mybatisplus.annotation.*;
import com.gitee.sunchenbin.mybatis.actable.annotation.*;
import com.gitee.sunchenbin.mybatis.actable.constants.MySqlTypeConstant;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.io.Serializable;
import java.util.Date;
import java.math.BigDecimal;

@Builder
@Data
@NoArgsConstructor
@AllArgsConstructor
@TableName("department_info")
public class DepartmentInfoDO implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", comment = "主键", isNull = false, isKey = true ,isAutoIncrement = true)
    private Long id;

    @Column(name = "name", comment = "部门名称", isNull = false, length = 255)
    private String name;

    @Column(name = "code", comment = "部门编码", length = 255)
    private String code;

    @Column(name = "admin", comment = "部门管理员", length = 255)
    private String admin;

    @Column(name = "parent_id", comment = "上级部门ID")
    private Long parentId;

    @Column(name = "status", comment = "状态：0:待激活；1:正常（已激活）；-1:删除", type = MySqlTypeConstant.TINYINT,defaultValue = "1")
    private Integer status;

    @Column(name = "gmt_create", comment = "创建时间", isNull = false, type = MySqlTypeConstant.DATETIME)
    @TableField(fill = FieldFill.INSERT)
    private Date gmtCreate;

    @Column(name = "gmt_modified", comment = "修改时间", isNull = false, type = MySqlTypeConstant.DATETIME)
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private Date gmtModified;

    @Column(name = "create_by", comment = "创建人", isNull = false, length = 255)
    private String createBy;

    @Column(name = "modify_by", comment = "修改人", length = 255)
    private String modifyBy;

    // R12-FIX-DDL-01：seq 原误标 isAutoIncrement=true，与主键 id 冲突导致 MySQL 建表失败
    // （Incorrect table definition; there can be only one auto column and it must be defined as a key）
    @Column(name = "seq", comment = "顺序", type = MySqlTypeConstant.INT)
    private Integer seq;

}
