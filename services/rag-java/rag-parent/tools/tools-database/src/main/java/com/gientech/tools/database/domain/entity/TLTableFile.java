package com.gientech.tools.database.domain.entity;

import com.gientech.tools.database.infrastructure.enums.FileParseStatusEnum;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.Date;

/**
 * 数据表-上传文件表;
 *
 * @Author ： xiaomin.zuo@gientech.com
 * @date : 2025-7-30
 */
@Builder
@Data
@NoArgsConstructor
@AllArgsConstructor
public class TLTableFile implements Serializable, Cloneable {
    /**
     * 编号
     */
    private Long id;

    /**
     * 数据库编号
     */
    private Long databaseId;

    /**
     * 数据表编号
     */
    private Long tableId;

    /**
     * 原始文件名称
     */
    private String originalFilename;

    /**
     * 存储文件夹路径
     */
    private String folderPath;

    /**
     * 文件名称
     */
    private String fileName;

    /**
     * 存储对象名称
     */
    private String objectName;

    /**
     * 文件路径
     */
    private String filePath;

    /**
     * 文件大小
     */
    private Double fileSize;

    /**
     * 列数量
     */
    private Integer columnCount;

    /**
     * 行数量
     */
    private Long rowCount;

    /**
     * 状态
     */
    private String status;

    /**
     * 解析耗时(毫秒)
     */
    private Long useTime;

    /**
     * 错误信息
     */
    private String errorMsg;

    /**
     * 创建时间
     */
    private Date gmtCreate;

    /**
     * 更新时间
     */
    private Date gmtModified;

    /**
     * 创建人
     */
    private String createBy;

    /**
     * 更新人
     */
    private String updateBy;

    public boolean isCreatedTable() {
        return !this.status.equals(FileParseStatusEnum.S10.getCode()) && !this.status.equals(FileParseStatusEnum.S11.getCode()) && !(this.status.equals(FileParseStatusEnum.S00.getCode()));
    }

}