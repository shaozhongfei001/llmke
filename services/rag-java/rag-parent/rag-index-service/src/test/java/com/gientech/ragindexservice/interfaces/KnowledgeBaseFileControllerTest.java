package com.gientech.ragindexservice.interfaces;

import com.alibaba.fastjson.JSON;
import com.gientech.ragcommon.index.request.FileMergeReq;
import com.gientech.ragindexservice.RagIndexServiceApplication;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
import org.springframework.web.multipart.MultipartFile;

import java.io.FileInputStream;
import java.io.IOException;
import java.io.File;
import java.security.DigestInputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;

@SpringBootTest(classes = {RagIndexServiceApplication.class})
@AutoConfigureMockMvc
public class KnowledgeBaseFileControllerTest {

    @Autowired
    private MockMvc mockMvc;

    private Long kbId = 838L;

    private String path;

    private String fileName;

    private String fileMd5;

    // Minio要求分块大小至少要5MB
    private int chunkSize = 5 * 1024 * 1024;

    @BeforeEach
    void setUp() throws IOException, NoSuchAlgorithmException {
        kbId = 838L;
        path = "C:\\Users\\dingh\\Documents\\RAG知识库素材\\";
        fileName = "2024年工商银行人工智能大模型白皮书.pdf";
        fileMd5 = getFileMd5(path + fileName);
    }

    @AfterEach
    void tearDown() {
    }

    @Test
    void checkCunkFile() throws Exception {
        int expectedDataValue = -1;
        mockMvc.perform(MockMvcRequestBuilders.get("/knowledgeBase/file/check")
                        .param("kbId", kbId.toString())
                        .param("fileName", fileName)
                        .param("fileMd5", fileMd5))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.errorMsg").isEmpty())
                .andExpect(jsonPath("$.errorCode").isEmpty())
                .andExpect(jsonPath("$.data").value(expectedDataValue));

    }

    @Test
    void chunkUpload() throws Exception {
        List<MockMultipartFile> chunks = chunkFile(path + fileName, chunkSize);
        for (MockMultipartFile chunk : chunks) {
            Boolean expectedDataValue = true;
            mockMvc.perform(MockMvcRequestBuilders.multipart("/knowledgeBase/file/upload")
                            .file(chunk)
                            .param("fileMd5", fileMd5))
                    .andExpect(status().isOk())
                    .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                    .andExpect(jsonPath("$.success").value(true))
                    .andExpect(jsonPath("$.errorMsg").isEmpty())
                    .andExpect(jsonPath("$.errorCode").isEmpty())
                    .andExpect(jsonPath("$.data").value(expectedDataValue));

        }
    }

    @Test
    void chunkMerge() throws Exception {
        FileMergeReq fileMergeReq = new FileMergeReq();
        fileMergeReq.setKbId(kbId);
        fileMergeReq.setFileName(fileName);
        fileMergeReq.setFileMd5(fileMd5);
        List<MockMultipartFile> chunks = chunkFile(path + fileName, chunkSize);
        fileMergeReq.setChunks(chunks.size());
        String requestJson = JSON.toJSONString(fileMergeReq);

        Boolean expectedDataValue = true;
        mockMvc.perform(MockMvcRequestBuilders.post("/knowledgeBase/file/merge")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(requestJson))
                .andExpect(status().isOk())
                .andExpect(content().contentType(MediaType.APPLICATION_JSON))
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.errorMsg").isEmpty())
                .andExpect(jsonPath("$.errorCode").isEmpty())
                .andExpect(jsonPath("$.data").value(expectedDataValue));


    }

    private String getFileMd5(String filePath) throws IOException, NoSuchAlgorithmException {
        // 创建 MD5 消息摘要实例
        MessageDigest digest = MessageDigest.getInstance("MD5");
        File file = new File(filePath);

        try (FileInputStream fis = new FileInputStream(file);
             DigestInputStream dis = new DigestInputStream(fis, digest)) {

            // 缓冲区大小，可根据需要调整
            byte[] buffer = new byte[8192];
            while (dis.read(buffer) != -1) {
                // 继续读取文件，DigestInputStream 会自动更新摘要
            }
        }

        // 获取最终的 MD5 哈希值
        byte[] hash = digest.digest();

        // 将字节数组转换为十六进制字符串
        StringBuilder hexString = new StringBuilder();
        for (byte b : hash) {
            String hex = Integer.toHexString(0xFF & b);
            if (hex.length() == 1) {
                hexString.append('0');
            }
            hexString.append(hex);
        }

        return hexString.toString();
    }

    private List<MockMultipartFile> chunkFile(String filePath, int chunkSize) throws IOException {
        List<MockMultipartFile> chunkedFiles = new ArrayList<>();
        File file = new File(filePath);
        try (FileInputStream fis = new FileInputStream(file)) {
            byte[] buffer = new byte[chunkSize];
            int bytesRead;
            int chunkNumber = 0;
            while ((bytesRead = fis.read(buffer)) != -1) {
                byte[] chunkData = new byte[bytesRead];
                System.arraycopy(buffer, 0, chunkData, 0, bytesRead);
                // String chunkFileName = file.getName() + ".part" + chunkNumber;
                // 现在合并方法要求分块文件名必须是分块数字
                String chunkFileName = String.valueOf(chunkNumber);
                MockMultipartFile chunk = new MockMultipartFile(
                        "file",
                        chunkFileName,
                        "application/octet-stream",
                        chunkData
                );
                chunkedFiles.add(chunk);
                chunkNumber++;
            }
        }
        return chunkedFiles;
    }

}