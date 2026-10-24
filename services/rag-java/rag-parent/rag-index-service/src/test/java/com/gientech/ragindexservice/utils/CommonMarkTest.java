package com.gientech.ragindexservice.utils;

import com.gientech.ragindexservice.application.service.KnowledgeBaseListAppService;
import com.gientech.ragcommon.index.request.PageFileStreamReq;
import com.gientech.start.storage.exception.FileStorageException;
import com.vladsch.flexmark.parser.Parser;
import com.vladsch.flexmark.util.ast.Node;
import com.vladsch.flexmark.util.sequence.BasedSequence;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.HttpHeaders;

import java.io.*;
import java.nio.charset.StandardCharsets;


/**
 * @author chenjuan
 * @date 2025/8/1 13:17
 */
@SpringBootTest
public class CommonMarkTest {

    private final int blockNums = 100;


    @Autowired
    private KnowledgeBaseListAppService knowledgeBaseListAppService;
    @Test
    public void test() throws IOException {

        Reader reader = new FileReader("D://服务发布专利具体步骤.md");
        Parser parser = Parser.builder().build();
        Node document = parser.parseReader(reader);
        Node node = document.getFirstChild();
        StringBuilder blocks = new StringBuilder();
        for (int i = 1; i <= blockNums && node != null; i++) {
            BasedSequence content = node.getChars(); // 源码中的子串
//            int startOffset = content.getStartOffset(); // 在原 markdown 中的开始位置
//            int endOffset = content.getEndOffset();     // 结束位置（不包含）
            blocks.append(content);


//            System.out.println("==== Block ====");
//            System.out.println("Start offset: " + startOffset);
//            System.out.println("End offset: " + endOffset);
//            System.out.println("Content:\n" + content);


            node = node.getNext();
            if (node != null) {
                content.append("\n");
            }
        }


        InputStream in = new ByteArrayInputStream(
                blocks.toString().getBytes(StandardCharsets.UTF_8)
        );
        FileOutputStream fileOut = new FileOutputStream(new File("D://md-test0801.md"));

        byte[] buf = new byte[1024 * 8];
        while (true) {
            int read = 0;
            read = in.read(buf);
            if (read == -1) {
                break;
            }
            fileOut.write(buf, 0, read);
        }
    }

    @Test
    public void test2() throws IOException, FileStorageException {
        PageFileStreamReq pageFileStreamReq = new PageFileStreamReq();
        pageFileStreamReq.setConvertedFilePath("http://10.15.12.13:9000/dev-rag-data/测试南自/电压和电池容量的关系.md/V0/电压和电池容量的关系.md");
        pageFileStreamReq.setPageSize(1);
        pageFileStreamReq.setPageNo(1);
        HttpHeaders headers = new HttpHeaders();
        try(InputStream in = knowledgeBaseListAppService.pageFileStream(pageFileStreamReq, headers);
            FileOutputStream fileOut = new FileOutputStream(new File("D://md-test0805-4.md"))){
            byte[] buf = new byte[1024 * 8];
            while (true) {
                int read = 0;
                read = in.read(buf);
                if (read == -1) {
                    break;
                }
                fileOut.write(buf, 0, read);
            }
        }
    }



}
