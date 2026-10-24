package com.gientech.ragcommon.index.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * @author chenjuan
 * @date 2025/7/29 17:25
 */
@Data
public class PageFileStreamReq {
    @NotBlank(message = "文件地址不能为空")
    private String convertedFilePath;
    private Integer pageNo;
    private Integer pageSize;
    private boolean stream = true;


    public static PageFileStreamReq from(String convertedFilePath, boolean stream) {
        PageFileStreamReq pageFileStreamReq = new PageFileStreamReq();
        pageFileStreamReq.setConvertedFilePath(convertedFilePath);
        pageFileStreamReq.setPageNo(1);
        pageFileStreamReq.setPageSize(10);
        pageFileStreamReq.setStream(stream);
        return pageFileStreamReq;
    }
}
