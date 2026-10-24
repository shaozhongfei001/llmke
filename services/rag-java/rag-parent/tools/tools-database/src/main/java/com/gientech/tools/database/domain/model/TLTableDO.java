package com.gientech.tools.database.domain.model;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.gitee.sunchenbin.mybatis.actable.annotation.Column;
import com.gitee.sunchenbin.mybatis.actable.constants.MySqlTypeConstant;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.Date;

/**
 * 数据表信息;
 *
 * @Author ： xiaomin.zuo@gientech.com
 * @date : 2025-7-11
 */
@Builder
@Data
@NoArgsConstructor
@AllArgsConstructor
@TableName("tools_table")
public class TLTableDO implements Serializable, Cloneable {
    /**
     * 编号
     */
    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", isNull = false, comment = "主键", isKey = true, isAutoIncrement = true)
    private Long id;

    /**
     * 数据库编号
     */
    @Column(name = "database_id", comment = "数据库编号")
    private Long databaseId;

    /**
     * 业务表名
     */
    @Column(name = "business_name", comment = "业务表名", length = 100)
    private String businessName;

    /**
     * 物理表名
     */
    @Column(name = "physical_name", comment = "物理表名", length = 100)
    private String physicalName;

    /**
     * 表描述
     */
    @Column(name = "description", comment = "表描述", length = 3000)
    private String description;

    /**
     * 列数量
     */
    @Column(name = "column_count", comment = "列数量")
    private Integer columnCount;

    /**
     * 行数量
     */
    @Column(name = "row_count", comment = "行数量")
    private Long rowCount;

    /**
     * 创建时间
     */
    @Column(name = "gmt_create", comment = "创建时间")
    private Date gmtCreate;

    /**
     * 更新时间
     */
    @Column(name = "gmt_modified", comment = "更新时间")
    private Date gmtModified;

    /**
     * 创建人
     */
    @Column(name = "create_by", comment = "创建人", length = 50)
    private String createBy;

    /**
     * 更新人
     */
    @Column(name = "update_by", comment = "更新人", length = 50)
    private String updateBy;

    @Column(name = "is_gen_desc", comment = "更新人", length = 1, type = MySqlTypeConstant.TINYINT)
    private Boolean isGenDesc;

    @Column(name = "gen_desc_err_msg", comment = "更新人", length = 1024, type = MySqlTypeConstant.VARCHAR)
    private String genDescErrMsg;

    @Column(name = "gen_desc_status", comment = "更新人", length = 16, type = MySqlTypeConstant.VARCHAR)
    private String genDescStatus;


}