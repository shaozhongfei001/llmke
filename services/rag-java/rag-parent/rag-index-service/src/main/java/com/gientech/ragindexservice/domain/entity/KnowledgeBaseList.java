package com.gientech.ragindexservice.domain.entity;

import com.fasterxml.jackson.annotation.JsonIgnore;
import com.gientech.ragcommon.index.enmus.TempStatusEnums;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.codehaus.plexus.util.StringUtils;
import org.springframework.util.CollectionUtils;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Date;
import java.util.List;
import java.util.Objects;

@NoArgsConstructor
@AllArgsConstructor
@Builder
@Data
public class KnowledgeBaseList implements Serializable {

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
     * minIO文件的id
     */
    private String fileId;

    /**
     * 文件id
     */
    private String fileName;

    /**
     * 文件大小
     */
    private Double fileSize;

    /**
     * 路径
     */
    private String filePath;

    private String fullTextPath;

    private String convertedFilePath;

    /**
     * 解析后的表格路径
     */
    private String tableFilePaths;


    /**
     * 解析后的文件路径
     */
    private String parsedFilePath;

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
     * 修订时间
     */
    private String reviseDate;

    /**
     * 父文件名
     */
    private String parentFileName;

    /**
     * 版本号
     */
    private String version;

    /**
     * 文件夹id
     */
    private Long folderId;

    /**
     * 文件url地址(从网页获取的文件)
     */
    private String sourceUrl;

    private boolean chunking;

    /**
     * 文件的uid(uid是前端生成的,文档上传问答使用,通过uid来判断文件解析状态)
     */
    private String uid;

    /**
     * 1 临时文件,2 持久化文件 默认值是2
     */
    private Integer tempStatus = TempStatusEnums.PERSISTENCE.getCode();


    private Integer permission;

    /**
     * 文件组id,算法端生成
     */
    private String groupId;

    /**
     * 切片策略
     */
    private String chunkType;

    /**
     * 文件标签
     */
    private String fileLabel;

    private String label;

    private Integer isFolder;

    private List<String> imagePaths;

    public List<String> getImagePaths() {
        return CollectionUtils.isEmpty(imagePaths) ? Arrays.asList() : imagePaths;
    }

    @JsonIgnore
    public Long getCommonId() {
        if (Objects.nonNull(this.isFolder) && this.isFolder == 1) {
            return this.folderId;
        } else {
            return this.id;
        }
    }

    public String getConvertedFileName() {
        if (StringUtils.isNotEmpty(this.fileName)) {
            String prefix = this.fileName.substring(0, this.fileName.lastIndexOf("."));
            return String.join(".", prefix, getConvertedFileExtension());
        }
        return null;
    }

    public String getConvertedFileExtension() {
        return "pdf";
    }


    public boolean isConvertedFile() {
        return Arrays.asList("pdf", "xlsx","html", "xls", "csv", "jpeg", "jpg", "png", "gif", "webp", "bmp", "heic", "svg", "eps", "ai", "psd", "tiff", "raw", "avif").contains(getFileType());
    }

    public boolean isNeedConvert2Md(){
        return Arrays.asList("xlsx","xls","csv").contains(getFileType());
    }

    public String getFileType() {
        if (StringUtils.isNotEmpty(this.fileName)) {
            return fileName.substring(fileName.lastIndexOf(".") + 1);
        }
        return "";
    }

}
