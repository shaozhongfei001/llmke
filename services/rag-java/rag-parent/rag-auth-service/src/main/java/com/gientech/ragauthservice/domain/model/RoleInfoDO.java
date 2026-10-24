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
@TableName("role_info")
@TableComment("角色表")
public class RoleInfoDO implements Serializable {

    private static final long serialVersionUID = 1L;

    @Column(name = "is_dtl", defaultValue = "0", comment = "逻辑删除 是否删除 1是 0否")
    private String isDtl;

    @Column(name = "create_by", comment = "创建人", length = 128)
    private String createBy;

    @Column(name = "gmt_create", comment = "创建时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtCreate;

    @Column(name = "update_by", comment = "更新人", length = 128)
    private String updateBy;

    @Column(name = "gmt_modified", comment = "更新时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtModified;

    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", isNull = false, comment = "主键" ,isKey = true ,isAutoIncrement = true)
    private Long id;

    @Column(name = "name", comment = "角色名称", length = 128)
    private String name;

    @Column(name = "description", comment = "描述", length = 512)
    private String description;

    @Column(name = "seq", comment = "排序")
    private Long seq;

    @Column(name = "status", defaultValue = "1", comment = "状态 0 禁用 1 启用")
    private Integer status;

}
