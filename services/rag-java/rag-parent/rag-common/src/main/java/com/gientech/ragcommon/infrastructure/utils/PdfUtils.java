package com.gientech.ragcommon.infrastructure.utils;

import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.apache.pdfbox.pdmodel.PDDocument;

import java.io.IOException;
import java.io.InputStream;
import java.net.URL;

@Slf4j
public class PdfUtils {

    /**
     * R14-C-FIX-21：对象流提供者。
     * <p>
     * 原实现对 http(s) 路径一律 {@code new URL(filePath).openStream()}，即"匿名裸 HTTP 取对象"。
     * R13 撤销 MinIO 匿名读之后，这条路径必然 403：
     * <pre>
     * ERROR PdfUtils - Server returned HTTP response code: 403 for URL:
     *   http://127.0.0.1:19000/r12-rag/kb_9/docx-plain.docx/V0/docx-plain.docx
     * </pre>
     * 但 {@code PdfUtils} 是 rag-common 里的**静态工具**，拿不到 Spring 容器里的 MinIO 客户端，
     * 所以这里开一个静态钩子：由各业务服务在启动时注入"带凭据取流"的实现
     * （index/qa 均为 {@code FileStorageUtils#getInputStreamByUrl}）。
     * 未注册时退回旧行为，保证不改变没有存储依赖的调用方。
     */
    @FunctionalInterface
    public interface ObjectStreamProvider {
        InputStream open(String filePath) throws Exception;
    }

    private static volatile ObjectStreamProvider objectStreamProvider;

    public static void registerObjectStreamProvider(ObjectStreamProvider provider) {
        objectStreamProvider = provider;
        log.info("PdfUtils 已注册带凭据的对象流提供者: {}", provider == null ? "null" : provider.getClass().getName());
    }

    public static Integer getPdfPages(String filePath) {
        Integer numberOfPages = 0;
        if (StringUtils.isEmpty(filePath))
            return numberOfPages;
        ObjectStreamProvider provider = objectStreamProvider;
        if (provider != null) {
            // 优先走带凭据的存储客户端（MinIO），避免匿名 HTTP 403
            try (InputStream in = provider.open(filePath)) {
                if (in != null) {
                    return getPdfPages(in);
                }
            } catch (Exception e) {
                log.warn("PdfUtils 带凭据取流失败，回退 URL 直连: {} err={}", filePath, e.getMessage());
            }
        }
        try {
            URL url = new URL(filePath);
            PDDocument document = PDDocument.load(url.openStream());
            numberOfPages = document.getNumberOfPages();
            document.close();
        } catch (IOException e) {
            log.error(e.getMessage());
        }
        return numberOfPages;
    }

    public static Integer getPdfPages(InputStream inputStream) {
        Integer numberOfPages = 0;
        try {
            PDDocument document = PDDocument.load(inputStream);
            numberOfPages = document.getNumberOfPages();
            document.close();
        } catch (IOException e) {
            log.error(e.getMessage());
        } finally {
            if (inputStream != null) {
                try {
                    inputStream.close();
                } catch (IOException e) {
                    log.error(e.getMessage());
                }
            }

        }
        return numberOfPages;
    }
}
