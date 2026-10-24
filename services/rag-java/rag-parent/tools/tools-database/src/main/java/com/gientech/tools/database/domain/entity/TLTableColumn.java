package com.gientech.tools.database.domain.entity;

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
public class TLTableColumn {
    private static final long serialVersionUID = 1L;
    /** 编号 */
    private Long id ;

    /** 数据库编号 */
    private Long databaseId ;

    /** 数据表编号 */
    private Long tableId ;

    /** 业务列名 */
    private String businessName ;

    /** 物理列名 */
    private String physicalName ;

    /** 列描述 */
    private String description ;

    /** 数据类型 */
    private String dataType ;

    /** 创建时间 */
    private Date gmtCreate ;

    /** 更新时间 */
    private Date gmtModified ;

    /** 创建人 */
    private String createBy ;

    /** 更新人 */
    private String updateBy ;

}