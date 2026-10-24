package com.gientech.start.storage.model;

import lombok.Data;

/** 上传结果（R12 兼容实现）。 */
@Data
public class FileInfo {

    /** 可访问完整路径：endPoint/bucket/object */
    private String filePath;

    /** 对象名（bucket 内相对路径） */
    private String objectName;

    private String fileName;

    private String bucketName;

    /** 与原 starter 对齐：调用方 setFileSize(Double) */
    private Double fileSize;

    private String contentType;
}
