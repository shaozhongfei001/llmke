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

@Builder
@Data
@NoArgsConstructor
@AllArgsConstructor
@TableName("user_privilege")
@TableComment("用户-数据权限关联")
public class UserPrivilegeDO implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", isNull = false, comment = "id" ,isKey = true ,isAutoIncrement = true)
    private Long id;

    @Column(name = "target_id", isNull = false, comment = "配置id")
    private Long targetId;

    @Column(name = "user_id", comment = "用户id,-1代表所有人")
    private Long userId;

    @Column(name = "biz_type", isNull = false, comment = "1:知识库;2:检索配置;3:模型")
    private Integer bizType;

    @Column(name = "permission", isNull = false, comment = "0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限")
    private Integer permission;

    @Column(name = "is_del", comment = "是否删除 -1 删除  1 正常 默认值1", defaultValue = "1")
    private Integer isDel;

    @Column(name = "gmt_create", comment = "创建时间", type = MySqlTypeConstant.DATETIME)
    @TableField(fill = FieldFill.INSERT)
    private Date gmtCreate;

    @Column(name = "gmt_modified", comment = "更新时间", type = MySqlTypeConstant.DATETIME)
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private Date gmtModified;

    @Column(name = "create_by", comment = "创建人", length = 50)
    private String createBy;

    @Column(name = "update_by", comment = "更新人", length = 50)
    private String updateBy;

}
