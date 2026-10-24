package com.gientech.ragindexservice.domain.model;

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
@TableName("biz_label")
@TableComment("用户-数据权限关联")
public class BizLabelDO implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", comment = "id", isNull = false, isKey = true ,isAutoIncrement = true)
    private Long id;

    @Column(name = "target_id", comment = "资源id", isNull = false)
    private Long targetId;

    @Column(name = "label", comment = "label", isNull = false, length = 256)
    private String label;

    @Column(name = "biz_type", comment = "1:知识库;2:检索配置;3:模型;4:文件", isNull = false, type = MySqlTypeConstant.TINYINT)
    private Integer bizType;

    @Column(name = "gmt_create", comment = "创建时间", type = MySqlTypeConstant.DATETIME)
    @TableField(fill = FieldFill.INSERT)
    private Date gmtCreate;

    @Column(name = "gmt_modified", comment = "更新时间", type = MySqlTypeConstant.DATETIME)
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private Date gmtModified;

    @Column(name = "create_by", comment = "创建人", length = 50)
    @TableField(fill = FieldFill.INSERT)
    private String createBy;

    @Column(name = "update_by", comment = "更新人", length = 50)
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private String updateBy;

    @Column(name = "is_del", comment = "是否删除 -1 删除  1 正常 默认值1", defaultValue = "1")
    private Integer isDel;

    @TableField(exist = false)
    private String bizName;
}
