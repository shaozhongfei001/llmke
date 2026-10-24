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
import java.math.BigDecimal;

@Builder
@Data
@NoArgsConstructor
@AllArgsConstructor
@TableName("resource_interface")
@TableComment("权限接口关联")
public class ResourceInterfaceDO implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", comment = "主键", isNull = false, isKey = true ,isAutoIncrement = true)
    private Long id;

    @Column(name = "resource_id", comment = "权限id")
    private Long resourceId;

    @Column(name = "interface_id", comment = "接口id")
    private Long interfaceId;

    @Column(name = "is_del", comment = "是否删除 -1 删除  1 正常 默认值1", defaultValue = "1")
    private Integer isDel;

    @Column(name = "gmt_create", comment = "创建时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtCreate;

    @Column(name = "gmt_modified", comment = "更新时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtModified;

    @Column(name = "create_by", comment = "创建人", length = 50)
    private String createBy;

    @Column(name = "update_by", comment = "更新人", length = 50)
    private String updateBy;

}
