package com.gientech.tools.database.domain.model;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.gitee.sunchenbin.mybatis.actable.annotation.Column;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.util.Date;

/**
 * 表字段信息;
 * @Author ： xiaomin.zuo@gientech.com
 * @date : 2025-8-8
 */
@Builder
@AllArgsConstructor
@NoArgsConstructor
@Data
@TableName("tools_table_column")
public class TLTableColumnDO {
    private static final long serialVersionUID = 1L;
    /** 编号 */
    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", isNull = false, comment = "主键", isKey = true, isAutoIncrement = true)
    private Long id ;

    /** 数据库编号 */
    @Column(name = "database_id", comment = "数据库编号")
    private Long databaseId ;

    /** 数据表编号 */
    @Column(name = "table_id", comment = "数据表编号")
    private Long tableId ;
    /** 业务列名 */
    @Column(name = "business_name", comment = "业务列名", length = 100)
    private String businessName ;

    /** 物理列名 */
    @Column(name = "physical_name", comment = "物理列名", length = 100)
    private String physicalName ;

    /** 列描述 */
    @Column(name = "description", comment = "列描述", length = 500)
    private String description ;

    /** 数据类型 */
    @Column(name = "data_type", comment = "数据类型", length = 50)
    private String dataType ;

    /** 创建时间 */
    @Column(name = "gmt_create", comment = "创建时间")
    private Date gmtCreate ;

    /** 更新时间 */
    @Column(name = "gmt_modified", comment = "更新时间")
    private Date gmtModified ;

    /** 创建人 */
    @Column(name = "create_by", comment = "创建人", length = 50)
    private String createBy ;

    /** 更新人 */
    @Column(name = "update_by", comment = "更新人", length = 50)
    private String updateBy ;

}