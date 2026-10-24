package com.gientech.ragindexservice.domain.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import com.gientech.ragcommon.infrastructure.typehandler.StringListTypeHandler;
import com.gitee.sunchenbin.mybatis.actable.annotation.Column;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.Date;
import java.util.List;
import java.util.Objects;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class KbFileExt implements Serializable {


    private static final long serialVersionUID = 1L;

    /**
     * 主键
     */
    private Long id;

    /**
     * 知识库id
     */
    private Long kbId;

    /**
     * 知识库名称
     */
    private String kbName;

    /**
     * minIO文件的id
     */
    private String fileId;

    /**
     * 文件名称
     */
    private String fileName;

    /**
     * 文件大小
     */
    private String fileSize;

    /**
     * 路径
     */
    private String filePath;

    /**
     * 全文txt地址
     */
    private String fullTextPath;

    /**
     * 状态 0:删除 1:正常 2:解析中，3:解析成功 4: 解析失败
     */
    private Integer status;

    /**
     * 0:禁用;1启用
     */
    private Integer isEnable;

    /**
     * 创建人
     */
    private String createBy;

    /**
     * 创建时间
     */
    private Date gmtCreate;

    /**
     * 修改人
     */
    private String modifyBy;

    /**
     * 修改时间
     */
    private Date gmtModified;

    /**
     * 解析后的文件路径
     */
    private String parsedFilePath;

    /**
     * 1 文件解析；2 FAQ解析 3 图解析；4 文档上传问答; 5 从文件解析复制的文件或者FAQ导入的问答对文件; 10 文件解析&faq抽取
     */
    private Integer parseType;

    /**
     * 问答对数
     */
    private Integer aqCount;

    /**
     * faq抽取状态 1 未抽取；2 抽取中；3 抽取成功 4 抽取失败 默认值 1
     */
    private Integer faqExtractStatus;

    /**
     * 图解析状态 1 未解析；2 解析中 3 解析成功 4 解析失败
     */
    private Integer graphParseStatus;

    /**
     * 修订实时间
     */
    private String reviseDate;

    /**
     * 父文件名称
     */
    private String parentFileName;

    /**
     * 版本号
     */
    private String version;

    /**
     * 转化后的文件路径
     */
    private String convertedFilePath;

    /**
     * 文件夹id
     */
    private Long folderId;

    /**
     * 文件夹名称
     */
    private String folderName;

    /**
     * 文件url地址(从网页获取的文件)
     */
    private String sourceUrl;

    /**
     * 是否是文件夹 0:否  1:是
     */
    private Integer isFolder;

    /**
     * 是否做切分解析 0-否 1-是
     */
    private boolean chunking;

    /**
     * not exist in field 元素类型 1-知识库 2-文件夹 3-文件
     */
    private Integer elementType;

    private Long parentId;

    private Integer permission;

    /**
     * 文件/文件夹标签
     */
    private String label;

    /**
     * 表格解析后的文件路径
     */
    private String tableFilePaths;

    private String imagePaths;

    /**
     * 切片策略
     */
    private String chunkType;


    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        KbFileExt kbFileExt = (KbFileExt) o;
        return Objects.equals(id, kbFileExt.id) && Objects.equals(kbId, kbFileExt.kbId) && Objects.equals(fileId, kbFileExt.fileId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, kbId, fileId);
    }
}
