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
@TableName("resource_info")
@TableComment("资源表")
public class ResourceInfoDO implements Serializable {

    private static final long serialVersionUID = 1L;

    @Column(name = "is_dtl", defaultValue = "0", comment = "逻辑删除 是否删除 1是 0否")
    private String isDtl;

    @Column(name = "gmt_create", comment = "创建时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtCreate;

    @Column(name = "create_by", comment = "创建人", length = 128)
    private String createBy;

    @Column(name = "gmt_modified", comment = "修改时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtModified;

    @Column(name = "update_by", comment = "更新人", length = 128)
    private String updateBy;

    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", isNull = false, comment = "主键" ,isKey = true ,isAutoIncrement = true)
    private Long id;

    @Column(name = "name", comment = "名称", length = 128)
    private String name;

    @Column(name = "url", comment = "路径", length = 2048)
    private String url;

    @Column(name = "description", comment = "描述", length = 128)
    private String description;

    @Column(name = "icon", comment = "图标", length = 200)
    private String icon;

    @Column(name = "pid", comment = "父类id")
    private Long pid;

    @Column(name = "seq", comment = "排序")
    private Long seq;

    @Column(name = "status", defaultValue = "1", comment = "状态 0 禁用 1 启用")
    private String status;

    @Column(name = "resource_type", comment = "菜单类型 1:菜单;2:接口")
    private String resourceType;

    @Column(name = "code", comment = "编码", length = 64)
    private String code;

}
