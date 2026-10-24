package com.gientech.ragindexservice.application.common;

import com.gientech.ragindexservice.infrastructure.annotation.FileType;
import com.gientech.ragcommon.index.request.PageFileStreamReq;
import com.gientech.start.storage.exception.FileStorageException;
import com.gientech.start.storage.utils.FileStorageUtils;
import lombok.extern.slf4j.Slf4j;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.jetbrains.annotations.NotNull;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Component;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.Objects;

/**
 * @author chenjuan
 * @date 2025/8/4 13:29
 */
@Component
@FileType("pdf")
@Slf4j
public class PdfProcessor implements FileProcessor {

    private final FileStorageUtils fileStorageUtils;

    public PdfProcessor(FileStorageUtils fileStorageUtils) {
        this.fileStorageUtils = fileStorageUtils;
    }

    @Override
    public InputStream pageInputStream(PageFileStreamReq pageFileStreamReq, HttpHeaders headers) throws IOException, FileStorageException {
        try (InputStream inputStreamByUrl = getInputStreamByUrl(pageFileStreamReq.getConvertedFilePath())) {
            PDDocument document = PDDocument.load(inputStreamByUrl);
            int numberOfPages = document.getNumberOfPages();
            if (Objects.nonNull(headers)) {
                headers.add(X_TOTAL_PAGES_HEADER, String.valueOf(numberOfPages));
            }

            return getByteArrayInputStream(pageFileStreamReq, numberOfPages, document);
        }
    }

    @Override
    public Integer getTotalPages(String url) {
        return getNumberOfPages(url);
    }

    private Integer getNumberOfPages(String url) {
        try (InputStream inputStreamByUrl = getInputStreamByUrl(url)) {
            PDDocument document = PDDocument.load(inputStreamByUrl);
            return document.getNumberOfPages();
        } catch (FileStorageException | IOException e) {
            log.error(e.getMessage(), e);
            return 0;
        }
    }

    private static @NotNull ByteArrayInputStream getByteArrayInputStream(PageFileStreamReq pageFileStreamReq, int numberOfPages, PDDocument document) throws IOException {
        int pageNo = pageFileStreamReq.getPageNo();
        int pageSize = pageFileStreamReq.getPageSize();
        PDDocument subDoc = new PDDocument();
        int start = Math.min(pageNo - 1, numberOfPages - 1);
        int end = Math.min(start + pageSize, numberOfPages);
        for (int i = start; i < end; i++) {
            PDPage page = document.getPage(i);
            subDoc.addPage(page);
        }
        try (ByteArrayOutputStream subDocBaos = new ByteArrayOutputStream()) {
            subDoc.save(subDocBaos);
            subDoc.close();
            return new ByteArrayInputStream(subDocBaos.toByteArray());
        }
    }

    private InputStream getInputStreamByUrl(String convertedFilePath) throws IOException, FileStorageException {
        return fileStorageUtils.getInputStreamByUrl(convertedFilePath, null);
    }
}
