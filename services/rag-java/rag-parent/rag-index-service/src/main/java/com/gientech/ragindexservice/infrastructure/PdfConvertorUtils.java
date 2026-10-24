package com.gientech.ragindexservice.infrastructure;

import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.enmus.KbFileStatusEnums;
import com.gientech.ragcommon.index.enmus.LogTypeEnums;
import com.gientech.ragcommon.index.enmus.ParseTaskStatusEnums;
import com.gientech.ragcommon.index.enmus.PlatFormEnums;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragindexservice.domain.entity.KnowledgeBaseList;
import com.gientech.ragindexservice.domain.service.FileParseTaskDomainService;
import com.gientech.ragindexservice.domain.service.KnowledgeBaseListDomainService;
import com.gientech.ragindexservice.domain.service.SynLogDomainService;
import com.gientech.start.storage.model.FileInfo;
import com.gientech.start.storage.utils.FileStorageUtils;
import com.google.common.collect.Lists;
import fr.opensagres.poi.xwpf.converter.core.IXWPFConverter;
import fr.opensagres.poi.xwpf.converter.pdf.PdfConverter;
import fr.opensagres.poi.xwpf.converter.pdf.PdfOptions;
import lombok.extern.slf4j.Slf4j;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.codehaus.plexus.util.StringUtils;
import org.jodconverter.core.DocumentConverter;
import org.jodconverter.core.document.DefaultDocumentFormatRegistry;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.stereotype.Component;

import java.io.*;
import java.util.List;

import static com.gientech.ragcommon.index.constant.IndexConstant.*;

/**
 * @author chenjuan
 * @date 2025/5/30 16:09
 */
@Component
@Slf4j
@RefreshScope
public class PdfConvertorUtils {

    private final DocumentConverter converter;

    private FileStorageUtils fileStorageUtils;

    private final SynLogDomainService synLogDomainService;

    private KnowledgeBaseListDomainService knowledgeBaseFileDomainService;

    private FileParseTaskDomainService fileParseTaskDomainService;

    @Value("${file-convert.error-msg.word}")
    private  String wordConverErrorMsg;

    @Value("${file-convert.error-msg.ppt}")
    private  String pptConverErrorMsg;

    @Value("${file-convert.error-msg.others}")
    private  String othersConverErrorMsg;

    public PdfConvertorUtils(DocumentConverter converter, FileStorageUtils fileStorageUtils, SynLogDomainService synLogDomainService, KnowledgeBaseListDomainService knowledgeBaseFileDomainService, FileParseTaskDomainService fileParseTaskDomainService) {
        this.converter = converter;
        this.fileStorageUtils = fileStorageUtils;
        this.synLogDomainService = synLogDomainService;
        this.knowledgeBaseFileDomainService = knowledgeBaseFileDomainService;
        this.fileParseTaskDomainService = fileParseTaskDomainService;
    }

    public boolean isNeedConvert(KnowledgeBaseList kbFile) {
        //当convertedFilePath为空且是应该转为pdf的文件类型
        return StringUtils.isBlank(kbFile.getConvertedFilePath()) && !kbFile.isConvertedFile();
    }

    /**
     * 把kbFile转成pdf并存到minio指定地方
     *
     * @param kbFile
     * @param primitiveName realPrimitiveName
     * @param platform
     * @param userId
     */
    public String kbFile2Pdf(KnowledgeBaseList kbFile,String primitiveName, String platform, String userId, Long taskId) {
        String folder = getFolder(platform, userId, primitiveName, kbFile.getParentFileName(), kbFile.getVersion());
        String pdfObjectName = folder + kbFile.getConvertedFileName();
        log.info("要转化pdf的文件地址:{}", kbFile.getFilePath());

        InputStream inputStream = null;
        ByteArrayOutputStream pdfOutputStream = null;
        ByteArrayInputStream pdfInputStream = null;
        XWPFDocument doc = null;
        String fileName = kbFile.getFileName();
        String fileType = fileName.substring(fileName.lastIndexOf(".") + 1);
        String errorMsg = othersConverErrorMsg;
        try {
            log.info("转pdf文件名: {}", kbFile.getFileName());

            inputStream = fileStorageUtils.getInputStreamByUrl(kbFile.getFilePath(), null);
            pdfOutputStream = new ByteArrayOutputStream();
            // R12-FIX-CONV-01：原实现直接 convert(InputStream)，JodConverter 会写一个无扩展名的
            // tempfile_N 交给 LibreOffice，LO 无法识别格式 → "Could not open document: tempfile_0"。
            // pptx 没有 XWPF 兜底（只有 docx 有），因此必失败。改为落临时文件（带真实扩展名）再转换。
            java.nio.file.Path tmpSource = java.nio.file.Files.createTempFile("r12conv-", "." + fileType);
            try {
                java.nio.file.Files.copy(inputStream, tmpSource, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
                converter.convert(tmpSource.toFile())
                        .to(pdfOutputStream)
                        .as(DefaultDocumentFormatRegistry.PDF)
                        .execute();
            } finally {
                try {
                    java.nio.file.Files.deleteIfExists(tmpSource);
                } catch (Exception ignore) {
                    // 临时文件清理失败不影响主流程
                }
            }
            byte[] byteArray = pdfOutputStream.toByteArray();
            pdfInputStream = new ByteArrayInputStream(byteArray);
            //存pdf
            FileInfo fileInfo = fileStorageUtils.putObject(folder, MultipartFileUtils.convertToMultipartFile(pdfInputStream, kbFile.getConvertedFileName()), null);
            kbFile.setFileSize(fileInfo.getFileSize());
            kbFile.setConvertedFilePath(fileInfo.getFilePath());
            kbFile.setParsedFilePath(fileInfo.getFilePath());
            log.info("convertedFilePath:{}", kbFile.getConvertedFilePath());
            knowledgeBaseFileDomainService.update(kbFile);
        } catch (Exception ex) {
            log.error("libreoffice convert filePath:{},error msg:{}", kbFile.getFilePath(), ex.getMessage());
            if (FILE_TYPE_WORD.contains(fileType)) {
                // R12-FIX-CONV-03：原逻辑用 XWPFDocument(xdocreport) 兜底转 PDF。实测该转换不嵌入中文字体，
                // 生成的 PDF 文本层**丢失全部汉字**（Milvus/ES 里只剩 ASCII 与标点，offset 从 ~600 字缩到 47 字），
                // 会静默毁掉中文语料。改为回落原始 docx，由解析服务 deepdoc DOCXParser 直接解析（中英文完整）。
                // 影响：docx 无 PDF 预览（前端预览降级），正文/表格进入索引；已登记为已知限制。
                log.warn("docx 转 PDF 不可用（LibreOffice 缺 writer 过滤器 / XWPF 中文丢字），回落直接解析原始 docx：{}",
                        kbFile.getFilePath());
                kbFile.setConvertedFilePath(kbFile.getFilePath());
                kbFile.setParsedFilePath(kbFile.getFilePath());
                knowledgeBaseFileDomainService.update(kbFile);
            } else if (FILE_TYPE_PPT.contains(fileType)) {
                // R12-FIX-CONV-02：本机 LibreOffice 缺少 writer/impress 过滤器（只有 core/common/math），
                // 任何 office 文件都无法转换（已验证 soffice CLI 对 .txt 也报 source file could not be loaded）。
                // pptx 又没有 docx 的 XWPF 兜底，原逻辑会直接判失败，导致 PPTX 完全不可解析。
                // 处理：不阻断解析，回落到原始文件交给解析服务（deepdoc 自带 PPTParser 可解析 pptx 文本/表格）。
                // 影响：PPTX 无 PDF 预览（前端预览降级），但正文/表格进入索引与检索；已登记为已知限制。
                log.warn("pptx 转 PDF 失败，回落为直接解析原始文件：{}，原因：{}", kbFile.getFilePath(), ex.getMessage());
                kbFile.setConvertedFilePath(kbFile.getFilePath());
                kbFile.setParsedFilePath(kbFile.getFilePath());
                knowledgeBaseFileDomainService.update(kbFile);
            } else {
                if (DOC.equals(fileType)){
                    errorMsg = wordConverErrorMsg;
                }else if(FILE_TYPE_PPT.contains(fileType))
                    errorMsg = pptConverErrorMsg;
                updateFailStatus(kbFile, taskId,errorMsg, ex.getMessage());
                throw new ApplicationException(ErrCodeEnum.LIBREOFFICE_ERROR);
            }
        } finally {

            if (inputStream != null) {
                try {
                    inputStream.close();
                } catch (IOException e) {
                    log.error(e.getMessage());
                }
            }

            if (pdfOutputStream != null) {
                try {
                    pdfOutputStream.close();
                } catch (IOException e) {
                    log.error(e.getMessage());
                }
            }

            if (pdfInputStream != null) {
                try {
                    pdfInputStream.close();
                } catch (IOException e) {
                    log.error(e.getMessage());
                }
            }

            if (doc != null) {
                try {
                    doc.close();
                } catch (IOException e) {
                    log.error(e.getMessage());
                }
            }

        }
        return pdfObjectName;
    }

    public static double calculateFileSizeMB(InputStream inputStream) throws IOException {
        byte[] buffer = new byte[8192];
        long totalBytes = 0;
        int bytesRead;

        while ((bytesRead = inputStream.read(buffer)) != -1) {
            totalBytes += bytesRead;
        }

        return totalBytes / (1024.0 * 1024.0); // 转为 MB，保留小数
    }

    private void updateFailStatus(KnowledgeBaseList kbFile, Long taskId, String errorMsg,String errorDetail) {
        knowledgeBaseFileDomainService.updateStatusByIds(Lists.newArrayList(kbFile.getId()), KbFileStatusEnums.PARSE_FAIL.getValue(), false);
        fileParseTaskDomainService.updateStatusByIds(List.of(taskId), ParseTaskStatusEnums.DEAL_FAIL.getCode());
        //记录失败日志
        synLogDomainService.saveLog(kbFile.getKbId(), kbFile.getId(), LogTypeEnums.FILE_PARSE.getCode(), null, errorMsg,errorDetail);
    }

    /**
     * @param platform       平台标识
     * @param userId         用户id
     * @param primitiveName  此为kbName
     * @param parentFileName 父文件夹
     * @param version        版本
     * @return String
     */
    public String getFolder(String platform, String userId, String primitiveName, String parentFileName, String version) {
        if (!platform.equals(PlatFormEnums.RAG_QA.getCode())) {
            return String.format("%s/%s/%s/%s/%s/", platform, userId, primitiveName, parentFileName, version);
        } else {
            return String.format("%s/%s/%s/", primitiveName, parentFileName, version);
        }
    }

}
