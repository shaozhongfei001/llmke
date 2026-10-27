package com.gientech.ragqaservice.infrastructure;

import com.gientech.ragcommon.infrastructure.utils.PdfUtils;
import com.gientech.start.storage.utils.FileStorageUtils;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * R14-C-FIX-21（qa 侧）：把"带凭据的 MinIO 取流"注入 {@link PdfUtils} 的静态钩子。
 * 见 index 侧同名类的说明：R13 撤匿名读后，`new URL(filePath).openStream()` 必 403。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class PdfStreamProviderRegistrar {

    private final FileStorageUtils fileStorageUtils;

    @PostConstruct
    public void register() {
        PdfUtils.registerObjectStreamProvider(path -> fileStorageUtils.getInputStreamByUrl(path, null));
        log.info("R14-C-FIX-21 PdfUtils 使用带凭据的对象流（qa）");
    }
}
