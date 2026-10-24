package com.gientech.tools.database.domain.model;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.gitee.sunchenbin.mybatis.actable.annotation.Column;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.Date;

/**
 * 数据表-上传文件表;
 * @Author ： xiaomin.zuo@gientech.com
 * @date : 2025-7-30
 */
@Builder
@Data
@NoArgsConstructor
@AllArgsConstructor
@TableName("tools_table_file")
public class TLTableFileDO implements Serializable,Cloneable{
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

    /** 原始文件名称 */
    @Column(name = "original_filename", comment = "原始文件名称")
    private String originalFilename;

    /** 存储文件夹路径 */
    @Column(name = "folder_path", comment = "存储文件夹路径")
    private String folderPath;

    /** 文件名称 */
    @Column(name = "file_name", comment = "文件名称")
    private String fileName ;

    /** 存储对象名称 */
    @Column(name = "object_name", comment = "存储对象名称")
    private String objectName ;

    /** 文件路径 */
    @Column(name = "file_path", comment = "文件路径")
    private String filePath ;

    /** 文件大小 */
    @Column(name = "file_size", comment = "文件大小")
    private Double fileSize ;


    /** 列数量 */
    @Column(name = "column_count", comment = "列数量")
    private Integer columnCount ;

    /** 行数量 */
    @Column(name = "row_count", comment = "行数量")
    private Long rowCount ;

    /** 状态 */
    @Column(name = "status", comment = "解析状态")
    private String status ;

    /** 解析耗时(毫秒) */
    @Column(name = "use_time", comment = "解析耗时(毫秒)")
    private Long useTime ;

    /** 错误信息 */
    @Column(name = "error_msg", comment = "错误信息", length = 1000)
    private String errorMsg ;

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