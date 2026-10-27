package com.gientech.ragindexservice.infrastructure;

import com.gientech.ragcommon.infrastructure.utils.PdfUtils;
import com.gientech.start.storage.utils.FileStorageUtils;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * R14-C-FIX-21：把"带凭据的 MinIO 取流"注入 {@link PdfUtils} 的静态钩子。
 * <p>
 * 背景：R13 撤销 MinIO 匿名读后，PdfUtils 的 `new URL(filePath).openStream()` 一律 403，
 * 表现为 Office/PDF 的 pdfPages 取不到（日志 `Server returned HTTP response code: 403`）。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class PdfStreamProviderRegistrar {

    private final FileStorageUtils fileStorageUtils;

    @PostConstruct
    public void register() {
        PdfUtils.registerObjectStreamProvider(path -> fileStorageUtils.getInputStreamByUrl(path, null));
        log.info("R14-C-FIX-21 PdfUtils 使用带凭据的对象流（index）");
    }
}
