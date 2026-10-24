package com.gientech.ragindexservice.domain.entity;

import com.gientech.ragcommon.index.enmus.FileListTypeEnums;
import lombok.Data;
import org.codehaus.plexus.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;

import java.io.Serializable;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Arrays;
import java.util.Locale;

@Data
public class KbFile implements Serializable {

    /**
     * 知识库id
     */
    private Long kbId;

    /**
     * 文件名称
     */
    private String fileName;

    /**
     * 列表类型: 1 文件解析列表；2 FAQ解析列表 默认值 1
     */
    private Integer fileListType = FileListTypeEnums.FILE_LIST.getCode();

    /**
     * 父文件名
     */
    private String parentFileName;

    /**
     * 版本号
     */
    private String version;

    /**
     * 文件流
     */
    private MultipartFile multipartFile;

    /**
     * 是否是多版本
     */
    private Boolean isMultipleVersion = false;

    /**
     * 文件objectName
     */
    private String objectName;


    private String convertedObjectName;

    /**
     * 文件大小
     */
    private Double fileSize;

    /**
     * 文件夹id
     */
    private Long folderId;

    /**
     * 文件导入url
     */
    private String sourceUrl;

    private boolean chunking;

    /**
     * 文件的uid(uid是前端生成的,文档上传问答使用,通过uid来判断文件解析状态)
     */
    private String uid;

    /**
     * 文件集hash，由算法端生成
     */
    private  String groupId;


    public String getExtensionByFileName() {
        if (StringUtils.isNotEmpty(this.fileName)) {
            return this.fileName.substring(this.fileName.lastIndexOf(".") + 1).toLowerCase(Locale.ENGLISH);
        }
        return null;
    }

    public void setConvertedObjectName(String fileType) {
        if (StringUtils.isNotEmpty(this.objectName)) {
            String prefix = this.objectName.substring(0, this.objectName.lastIndexOf("."));
            this.convertedObjectName = String.join(".", prefix, fileType);
        }
    }

    public void setConvertedObjectName() {
        if (StringUtils.isNotEmpty(this.objectName)) {
            String prefix = this.objectName.substring(0, this.objectName.lastIndexOf("."));
            this.convertedObjectName = String.join(".", prefix, getConvertedFileExtension());
        }
    }

    public String getConvertedFileName() {
        if (StringUtils.isNotEmpty(this.fileName)) {
            String prefix = this.fileName.substring(0, this.fileName.lastIndexOf("."));
            return String.join(".", prefix, getConvertedFileExtension());
        }
        return null;
    }

    public String getConvertedFileName(String fileType) {
        if (StringUtils.isNotEmpty(this.fileName)) {
            String prefix = this.fileName.substring(0, this.fileName.lastIndexOf("."));
            return String.join(".", prefix, fileType);
        }
        return null;
    }

    public double getConvertedFileSize(long byteLength) {
        return (BigDecimal.valueOf((double) byteLength / 1048576.0)).setScale(2, RoundingMode.valueOf(4)).doubleValue();
    }

    public String getConvertedFileExtension() {
        return "pdf";
    }

    public boolean isConvertedFile(String fileType) {
        return Arrays.asList("pdf", "xlsx", "xls", "csv","jpeg","jpg", "png", "gif", "webp", "bmp", "heic", "svg", "eps" ,"ai", "psd", "tiff", "raw", "avif").contains(fileType);
    }

    public String getFileName() {
        if (StringUtils.isNotEmpty(fileName))
            fileName = fileName.replace(" ", "");
        return fileName;
    }
}
