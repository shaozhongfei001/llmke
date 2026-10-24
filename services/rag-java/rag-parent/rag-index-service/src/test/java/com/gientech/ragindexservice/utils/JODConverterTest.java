package com.gientech.ragindexservice.utils;

import org.jodconverter.core.DocumentConverter;
import org.jodconverter.core.document.DefaultDocumentFormatRegistry;
import org.jodconverter.core.office.OfficeException;
import org.jodconverter.remote.RemoteConverter;
import org.jodconverter.remote.office.RemoteOfficeManager;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.io.*;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/11/15 18:29
 */
@SpringBootTest
public class JODConverterTest {

    @Autowired
    private DocumentConverter converter;

    @Test
    void contextLoads() throws OfficeException, FileNotFoundException {
        InputStream inputStream = new FileInputStream("E:\\gien_data\\document\\RAG\\文件集\\html\\三江高频2023年调查报告(1).html");
        OutputStream outputStream = new FileOutputStream("E:\\gien_data\\document\\RAG\\文件集\\html\\三江高频2023年调查报告(2).HTML");
        converter.convert(inputStream)
                .to(outputStream)
                .as(DefaultDocumentFormatRegistry.HTML)
                .execute();
//        RemoteOfficeManager officeManager = RemoteOfficeManager.builder()
//                .urlConnection("http://10.15.12.12:9999") // 设置远程服务的 URL
//                .build();
//        officeManager.start();
//
//        // 创建 RemoteConverter
//        RemoteConverter converter = RemoteConverter.make(officeManager);
//        File inputFile = new File("E:\\gien_data\\project\\gien-rag\\rag-parent\\rag-index-service\\src\\test\\java\\com\\gientech\\ragindexservice\\utils\\上网流程.docx");
//        File outputFile = new File("E:\\gien_data\\project\\gien-rag\\rag-parent\\rag-index-service\\src\\test\\java\\com\\gientech\\ragindexservice\\utils\\上网流程.pdf");
//        converter.convert(inputFile)
//                .to(outputFile).execute();

    }
}
