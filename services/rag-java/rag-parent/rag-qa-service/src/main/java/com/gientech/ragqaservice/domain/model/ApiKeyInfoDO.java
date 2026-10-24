package com.gientech.ragqaservice.domain.model;

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
@TableName("api_key_info")
@TableComment("apikey的信息")
public class ApiKeyInfoDO implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", comment = "主键", isNull = false, isKey = true ,isAutoIncrement = true)
    private Long id;

    @Column(name = "api_key", comment = "apikey全局唯一", isNull = false, length = 512)
    private String apiKey;

    @Column(name = "target_id", comment = "目标id")
    private Integer targetId;

    @Column(name = "status", comment = "状态 0:禁用；1:正常 默认值1", defaultValue = "1")
    private Integer status;

    @Column(name = "biz_type", comment = "业务类型 1:助手配置", isNull = false, defaultValue = "1", type = MySqlTypeConstant.TINYINT)
    private Integer bizType;

    @Column(name = "expire_time", comment = "过期时间", isNull = false, type = MySqlTypeConstant.DATETIME)
    private Date expireTime;

    @Column(name = "is_del", comment = "是否删除 -1 删除  1 正常 默认值1", defaultValue = "1")
    private Integer isDel;

    @Column(name = "create_by", comment = "创建人", length = 30)
    private String createBy;

    @Column(name = "gmt_create", comment = "创建时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtCreate;

    @Column(name = "modify_by", comment = "修改人", length = 30)
    private String modifyBy;

    @Column(name = "gmt_modified", comment = "修改时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtModified;

}
