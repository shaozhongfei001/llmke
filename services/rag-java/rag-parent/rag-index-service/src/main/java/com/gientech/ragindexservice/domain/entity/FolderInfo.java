package com.gientech.ragindexservice.domain.entity;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.util.Date;

@AllArgsConstructor
@NoArgsConstructor
@Builder
@Data
public class FolderInfo {

    private static final long serialVersionUID = 1L;

    /**
     * 主键
     */
    private Long id;

    /**
     * 文件夹名称
     */
    private String name;

    /**
     * 知识库id
     */
    private Long kbId;

    /**
     * 1:文档解析；2:FAQ抽取; 3;知识图谱 4:FAQ管理创建的文件夹或者从FAQ抽取复制的文件夹
     */
    private Integer type;

    /**
     * 父文件夹id
     */
    private Long parentId;

    /**
     * 文件夹标签
     */
    private String folderLabel;

    /**
     * 1：正常；-1：删除
     */
    private Integer status;

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

    /**
     * 完整路径（包含结尾/)
     */
    private String fullPath;

}
