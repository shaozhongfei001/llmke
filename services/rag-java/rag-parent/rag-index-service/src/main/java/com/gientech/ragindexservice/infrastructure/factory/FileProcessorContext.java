package com.gientech.ragindexservice.infrastructure.factory;

import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragcommon.infrastructure.utils.FileUtils;
import com.gientech.ragindexservice.application.common.FileProcessor;
import com.gientech.ragindexservice.infrastructure.annotation.FileType;
import com.gientech.ragcommon.index.request.PageFileStreamReq;
import com.gientech.start.storage.exception.FileStorageException;
import com.gientech.start.storage.utils.FileStorageUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.InputStream;
import java.util.*;

/**
 * @author chenjuan
 * @date 2025/8/4 13:22
 */
@Service
@Slf4j
public class FileProcessorContext {
    private final Map<String, FileProcessor> processorMap;

    @Autowired
    public FileProcessorContext(List<FileProcessor> processors, FileStorageUtils fileStorageUtils) {
        this.processorMap = new HashMap<>();
        for (FileProcessor p : processors) {
            FileType annotation = p.getClass().getAnnotation(FileType.class);
            if (annotation != null) {
                String type = annotation.value().toLowerCase();
                processorMap.put(type, p);
            }
        }
    }

    public InputStream pageInputStream(PageFileStreamReq pageFileStreamReq, HttpHeaders headers) throws IOException, FileStorageException {
        FileProcessor processor = getProcessor(pageFileStreamReq.getConvertedFilePath());
        return processor.pageInputStream(pageFileStreamReq, headers);
    }

    public Integer totalPages(String url) {
        try {
            FileProcessor processor = getProcessor(url);
            return processor.getTotalPages(url);
        } catch (Exception e) {
            return 0;
        }
    }

    private FileProcessor getProcessor(String url) {
        String fileType = FileUtils.getExt(url);
        log.info("fileType is {}", fileType);
        FileProcessor processor = processorMap.get(fileType.toLowerCase(Locale.ROOT));
        if (Objects.isNull(processor)) {
            throw new ApplicationException(ErrCodeEnum.PARAM_ILLEGAL.getErrCode(), "不支持的文件类型:" + fileType);
        }
        return processor;
    }
}
