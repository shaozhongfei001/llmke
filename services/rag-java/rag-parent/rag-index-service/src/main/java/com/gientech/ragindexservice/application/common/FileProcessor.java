package com.gientech.ragindexservice.application.common;

import com.gientech.ragcommon.index.request.PageFileStreamReq;
import com.gientech.start.storage.exception.FileStorageException;
import org.springframework.http.HttpHeaders;

import java.io.IOException;
import java.io.InputStream;

/**
 * @author chenjuan
 * @date 2025/8/4 13:24
 */
public interface FileProcessor {

    String X_TOTAL_PAGES_HEADER = "X-Total-Pages";
    /**
     * 分页获取文件的字节流
     * @param pageFileStreamReq 分页请求
     * @param headers 响应头中写入文件总页数
     * @return 字节流
     * @throws IOException 文件异常
     * @throws FileStorageException fileStorage异常
     */
    InputStream pageInputStream(PageFileStreamReq pageFileStreamReq, HttpHeaders headers) throws IOException, FileStorageException;

    /**
     * 获取总页数
     * @param url 文档url
     * @return 页数/块数 pdf和html返回总页数；md返回总块数
     */
    Integer getTotalPages(String url);
}
