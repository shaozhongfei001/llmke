package com.gientech.ragcommon.qa.dto;

import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.fastjson2.annotation.JSONField;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.apache.pdfbox.pdmodel.PDDocument;

import java.io.IOException;
import java.net.URL;
import java.util.Arrays;
import java.util.List;
import java.util.Objects;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/9/27 13:36
 */
@Data
@Slf4j
public class Document {

    @JSONField(name = "page_content")
    private String pageContent;

    @JSONField(name = "order_num")
    private String orderNum;

    private JSONObject metadata;

    private String type;

    private String parsedFilePath;

    private String sourceFileName;

    @JSONField(name = "pic_url_list")
    private JSONArray picUrlList;

    private String score;

    @JSONField(name = "rerank_score_rank")
    private String rerankScoreRank;

    @JSONField(name = "rrf_score")
    private String rrfScore;

    @JSONField(name = "rrf_score_rank")
    private String rrfScoreRank;

    @JSONField(name = "faq_answer")
    private String faqAnswer;

    @JSONField(name = "faq_question")
    private String faqQuestion;

    private Integer pdfPages;

    public void buildParsedFilePath(String minioUrl) {
        if (Objects.isNull(metadata)) {
            return;
        }
        String source = metadata.getString("source");
        String tableName = metadata.getString("table_name");
        if (StringUtils.isNotBlank(source)) {

            String objectName = source.substring(source.indexOf("/") + 1);
            String substring = objectName.substring(objectName.indexOf("/") + 1);
            sourceFileName = substring.substring(0,substring.indexOf("/"));

            String fileType = source.substring(source.lastIndexOf(".") + 1);
            if (Arrays.asList("xlsx","xls","csv").contains(fileType)) {
                String fileName = source.substring(source.lastIndexOf("/") + 1);
                String filePath = "";
                try {
                    if(StringUtils.isEmpty(tableName)) {
                        filePath = minioUrl + "/" + source.substring(0, source.lastIndexOf("/")) + "/parsed/" + fileName + ".md";
                    }else
                        filePath = minioUrl + "/" + source.substring(0, source.lastIndexOf("/")) + "/parsed/tables/" + tableName + ".md";
                } catch (Exception e) {
                    log.error(e.getMessage());
                }
                parsedFilePath = filePath;
            } else {
                parsedFilePath = minioUrl + "/" + source;
            }
            if (StringUtils.isNotBlank(fileType) && "pdf".equals(fileType))
                pdfPages = getPdfPages(parsedFilePath);
        }
    }

    private Integer getPdfPages(String filePath) {
        Integer numberOfPages = 0;
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
}
