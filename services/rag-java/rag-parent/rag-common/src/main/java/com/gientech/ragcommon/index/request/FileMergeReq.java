package com.gientech.ragcommon.index.request;
import lombok.Data;

@Data
public class FileMergeReq {

    /**
     * 知识库id
     */
    private Long kbId;

    /**
     * 文件名称
     */
    private String fileName;

    /**
     * 文件md5
     */
    private String fileMd5;

    /**
     * 总分片数量
     */
    private Integer chunks;
}
