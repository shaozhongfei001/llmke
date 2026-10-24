package com.gientech.ragindexservice.utils;

import com.gientech.ragindexservice.application.service.KnowledgeBaseListAppService;
import com.gientech.ragcommon.index.request.PageFileStreamReq;
import com.gientech.start.storage.exception.FileStorageException;
import com.gientech.start.storage.utils.FileStorageUtils;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.rendering.PDFRenderer;
import org.apache.tika.Tika;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;

import java.io.*;

/**
 * @author chenjuan
 * @date 2025/7/29 13:10
 */
@SpringBootTest
public class FileStorageUtilsTest {
    @Autowired
    private FileStorageUtils fileStorageUtils;

    @Autowired
    private KnowledgeBaseListAppService knowledgeBaseListAppService;

    @Test
    public void getInputStreamByUrl() throws IOException, FileStorageException {
        //测试url读流
        InputStream inputStream = fileStorageUtils.getInputStreamByUrl("http://10.15.12.13:9000/dev-rag-data/表格测试0108/表格测试0108_Q基金保有量点评权益型保有规模环比缩减券商渠道规模份额双增行业研报/V0/23Q2基金保有量点评：权益型保有规模环比缩减，券商渠道规模份额双增2023-07-24行业研报.pdf", null);
        FileOutputStream fileOut = new FileOutputStream(new File("D:\\test.pdf"));
        byte[] buf = new byte[1024 * 8];
        while (true) {
            int read = 0;
            if (inputStream != null) {
                read = inputStream.read(buf);
            }
            if (read == -1) {
                break;
            }
            fileOut.write(buf, 0, read);
        }
    }

    @Test
    public void getPageFromPdf() throws IOException {
        InputStream inputStream = new FileInputStream("D://test.pdf");
        PDDocument document = PDDocument.load(inputStream);
        PDFRenderer renderer = new PDFRenderer(document);
        PDDocument singlePage = new PDDocument();
        singlePage.addPage(document.getPage(0)); // page index从0开始
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        singlePage.save(out);
        ByteArrayInputStream in = new ByteArrayInputStream(out.toByteArray());
        singlePage.close();
        document.close();
        FileOutputStream fileOut = new FileOutputStream(new File("D://test-0-page.pdf"));
        byte[] pageBytes = out.toByteArray();
        byte[] buf = new byte[1024 * 8];
        while (true) {
            int read = 0;
            if (in != null) {
                read = in.read(buf);
            }
            if (read == -1) {
                break;
            }
            fileOut.write(buf, 0, read);
        }
    }

    @Test
    public void getFile() throws IOException, FileStorageException {
        PageFileStreamReq pageFileStreamReq = new PageFileStreamReq();
        pageFileStreamReq.setConvertedFilePath("http://10.15.12.13:9000/dev-rag-data/测试南自/中国电子规章制度汇编（2024版）-集团公司第二分册.pdf/V0/中国电子规章制度汇编（2024版）-集团公司第二分册.pdf");
        pageFileStreamReq.setPageSize(10);
        pageFileStreamReq.setPageNo(600);
        HttpHeaders headers = new HttpHeaders();
        InputStream in = knowledgeBaseListAppService.pageFileStream(pageFileStreamReq, headers);
        FileOutputStream fileOut = new FileOutputStream(new File("D://test0731.pdf"));
        byte[] buf = new byte[1024 * 8];
        while (true) {
            int read = 0;
            if (in != null) {
                read = in.read(buf);
            }
            if (read == -1) {
                break;
            }
            fileOut.write(buf, 0, read);
        }
    }

    @Test
    public void getMediaType() {
        byte[] mediaTypeByteArrayByUrl = fileStorageUtils.getMediaTypeByteArrayByUrl("http://10.15.12.13:9000/dev-rag-data/15bcf5b80e656812fa97d97c277f7604/保险行政处罚知识库_金罚决字号/V0/parsed/商保理赔FAQV2.xlsx.md", null);
        Tika tika = new Tika();
        String detect = tika.detect(mediaTypeByteArrayByUrl);
        MediaType mediaType = MediaType.parseMediaType(detect);

        System.out.println( mediaType);
    }

}
