package com.gientech.ragindexservice.application.common;

import com.gientech.ragindexservice.infrastructure.annotation.FileType;
import com.gientech.ragcommon.index.request.PageFileStreamReq;
import com.gientech.start.storage.exception.FileStorageException;
import com.gientech.start.storage.utils.FileStorageUtils;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.io.InputStream;

/**
 * @author chenjuan
 * @date 2025/8/5 13:34
 */
@Component
@FileType("html")
public class HtmlProcessor implements FileProcessor{

    private final FileStorageUtils fileStorageUtils;

    public HtmlProcessor(FileStorageUtils fileStorageUtils) {
        this.fileStorageUtils = fileStorageUtils;
    }

    @Override
    public InputStream pageInputStream(PageFileStreamReq pageFileStreamReq, HttpHeaders headers) throws IOException, FileStorageException {
        try(InputStream inputStreamUrl = fileStorageUtils.getInputStreamByUrl(pageFileStreamReq.getConvertedFilePath(),null)){
            return inputStreamUrl;
        }
    }

    @Override
    public Integer getTotalPages(String url) {
        return 1;
    }
}
