package com.gientech.ragauthservice.domain.model;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
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
import java.math.BigDecimal;

@Builder
@Data
@NoArgsConstructor
@AllArgsConstructor
@TableName("interface_info")
@TableComment("接口信息")
public class InterfaceInfoDO implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", comment = "主键", isNull = false, isKey = true ,isAutoIncrement = true)
    private Long id;

    @Column(name = "app_name", comment = "应用名称", length = 128)
    private String appName;

    @Column(name = "app_name_abbreviate", comment = "应用简称", length = 128)
    private String appNameAbbreviate;

    @Column(name = "name", comment = "接口名称", length = 128)
    private String name;

    @Column(name = "url", comment = "url", length = 128)
    private String url;

    @Column(name = "method", comment = "接口的请求方式", length = 16)
    private String method;

    @Column(name = "gmt_create", comment = "创建时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtCreate;

    @Column(name = "gmt_modified", comment = "更新时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtModified;

    @Column(name = "create_by", comment = "创建人", length = 50)
    private String createBy;

    @Column(name = "update_by", comment = "更新人", length = 50)
    private String updateBy;

    @TableField(exist = false)
    private Long resourceId;

    @TableField(exist = false)
    private String resourceName;

    @TableField(exist = false)
    private Integer resourceType;
}
