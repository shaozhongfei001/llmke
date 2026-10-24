package com.gientech.ragindexservice.application.common;

import com.gientech.ragindexservice.infrastructure.annotation.FileType;
import com.gientech.ragindexservice.infrastructure.cache.FileTotalPagesCache;
import com.gientech.ragcommon.index.request.PageFileStreamReq;
import com.gientech.start.storage.exception.FileStorageException;
import com.gientech.start.storage.utils.FileStorageUtils;
import com.vladsch.flexmark.parser.Parser;
import com.vladsch.flexmark.util.ast.Node;
import com.vladsch.flexmark.util.data.MutableDataSet;
import com.vladsch.flexmark.util.sequence.BasedSequence;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Component;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Objects;

/**
 * @author chenjuan
 * @date 2025/8/4 13:30
 * 参考资料：https://github.com/vsch/flexmark-java/wiki/Extensions#parser
 */
@Component
@FileType("md")
@Slf4j
public class MarkdownProcessor implements FileProcessor {

    private final FileStorageUtils fileStorageUtils;

    public MarkdownProcessor(FileStorageUtils fileStorageUtils) {
        this.fileStorageUtils = fileStorageUtils;
    }

    @Override
    public InputStream pageInputStream(PageFileStreamReq pageFileStreamReq, HttpHeaders headers) throws IOException, FileStorageException {
        Parser parser = getParser();
        try (InputStream inputStreamByUrl = fileStorageUtils.getInputStreamByUrl(pageFileStreamReq.getConvertedFilePath(), null);
             Reader reader = new InputStreamReader(inputStreamByUrl, StandardCharsets.UTF_8)) {
            Node doc = parser.parseReader(reader);

            Node node = doc.getFirstChild();
            StringBuilder blocks = new StringBuilder();
            Integer totalBlockNum = getTotalBlockNum(pageFileStreamReq.getConvertedFilePath());

            int pageNo = Math.min(pageFileStreamReq.getPageNo(), totalBlockNum);
            if (pageNo < 1) {
                pageNo = 1;
            }
            int pageSize = pageFileStreamReq.getPageSize();
            int end = Math.min(pageFileStreamReq.getPageNo() + pageSize, totalBlockNum);
            headers.add(X_TOTAL_PAGES_HEADER, String.valueOf(totalBlockNum));

            //跳过
            for (int i = 1; i < pageNo && Objects.nonNull(node); i++) {
                node = node.getNext();
            }
            //读取
            for (int i = pageNo; i <= end && Objects.nonNull(node); i++) {
                BasedSequence content = node.getChars();
                blocks.append(content);
                node = node.getNext();
            }
            return new ByteArrayInputStream(blocks.toString().getBytes(StandardCharsets.UTF_8));
        }
    }

    private Parser getParser() {
        MutableDataSet options = new MutableDataSet();
        options.set(Parser.BLANK_LINES_IN_AST, true);
        options.set(Parser.HEADING_PARSER, false);
        options.set(Parser.THEMATIC_BREAK_PARSER, false);
        options.set(Parser.BLOCK_QUOTE_PARSER, false);
        options.set(Parser.FENCED_CODE_BLOCK_PARSER, false);
        return Parser.builder(options).build();
    }

    @Override
    public Integer getTotalPages(String url) {
        return getTotalBlockNum(url);
    }

    private Integer getTotalBlockNum(String url) {
        try (InputStream inputStreamByUrl = fileStorageUtils.getInputStreamByUrl(url, null);
             Reader reader = new InputStreamReader(inputStreamByUrl, StandardCharsets.UTF_8)) {
            Integer blockCount = FileTotalPagesCache.getBlockCount(url);
            if (Objects.isNull(blockCount)) {
                log.info("markdown getTotalBlockNum blockCount not hit cache");
                blockCount = computeBlockCount(reader);
                FileTotalPagesCache.putBlockCount(url, blockCount);
            } else {
                log.info("markdown getTotalBlockNum blockCount hit cache");
            }
            return blockCount;
        } catch (FileStorageException | IOException e) {
            log.error(e.getMessage(), e);
            return 0;
        }

    }

    private Integer computeBlockCount(Reader reader) {
        try {
            int count = 0;
            Node doc = getParser().parseReader(reader);
            for (Node node = doc.getFirstChild(); node != null; node = node.getNext()) {
                count++;
            }
            log.info("markdown total blocks:{}", count);
            return count;
        } catch (IOException e) {
            log.error(e.getMessage(), e);
            log.error("computeBlockCount error!!", e);
            return 0;
        }
    }
}
