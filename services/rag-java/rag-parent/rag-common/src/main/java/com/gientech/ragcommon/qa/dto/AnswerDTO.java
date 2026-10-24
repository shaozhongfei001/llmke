package com.gientech.ragcommon.qa.dto;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Getter;
import lombok.Setter;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;

import java.util.Date;
import java.util.List;
import java.util.stream.Collectors;

import static com.gientech.ragcommon.qa.constant.AIConstant.DOCUMENTS;
import static com.gientech.ragcommon.qa.constant.AIConstant.WEB_DOCUMENTS_LIST;

/**
 * @Descrption:
 * @Author:ws
 * @Date:2024/06/04 09:36
 **/
@Schema(name = "回答响应体")
@Setter
@Getter
@Slf4j
public class AnswerDTO {

    /**
     * 主键
     */
    @Schema(name = "id", description = "主键")
    private Long id;

    /**
     * 创建时间
     */
    @Schema(name = "gmtCreate", description = "创建时间")
    private Date gmtCreate;


    /**
     * 内容
     */
    @Schema(name = "content", description = "回答内容")
    private String content;

    /**
     * TEXT：文本；VOICE：语音
     */
    @Schema(name = "type", description = "内容类型（TEXT：文本；VOICE：语音）")
    private String type;

    /**
     * 召回内容（json）
     */
    @Schema(name = "reference", description = "引用文章内容（召回内容）")
    private String reference;

    @Schema(name = "webReference", description = "联网引用文章内容（召回内容）")
    private String webReference;

    /**
     * 前端生成的uuid
     */
    @Schema(name = "queryId", description = "前端生成的提问id")
    private String queryId;

    @Schema(name = "feedbackResult", description = "反馈结果 0：踩；1：赞")
    private Integer feedbackResult;

    @Schema(name = "feedbackId", description = "反馈id")
    private Long feedbackId;

    private List<String> parsedFilePaths;

    @Schema(name = "recommendQuestion", description = "问题推荐")
    private String recommendQuestion;

    @Schema(name = "llmType", description = "推理类型 1:常推理接口, 2:表格推理接口 默认值1")
    private Integer llmType;

    @Schema(name = "resultType", description = "响应的类型 1:正常大模型推理; 2:FAQ; 3 命中敏感词;4 强知识依赖;5文档上传问答")
    private Integer resultType;

    @Schema(name = "respTime", description = "问答接口响应时间(毫秒)")
    private Long respTime;

    private String databaseReference;


    public void buildParsedFilePaths(String minioUrl) {
        if (StringUtils.isEmpty(reference))
            return;
        List<JSONObject> references = JSON.parseArray(reference, JSONObject.class);
        List<String> filePaths = references.stream().map(ref -> {
            JSONObject metadata = ref.getJSONObject("metadata");
            String source = metadata.getString("source");
            String fileName = source.substring(source.lastIndexOf("/") + 1);
            String filePath = "";
            try {
                filePath = minioUrl + "/" + source.substring(0, source.lastIndexOf("/")) + "/parsed/" + fileName.substring(0, fileName.lastIndexOf(".")) + ".txt";
            } catch (Exception e) {
                log.error(e.getMessage());
            }
            return filePath;
        }).collect(Collectors.toList());
        parsedFilePaths = filePaths;
    }

    public Integer getTokens() {
        return StringUtils.isEmpty(this.content) ? 0 : content.length();
    }

    public void setReference(String reference) {
        if(StringUtils.isNotEmpty(reference)){
            if (reference.contains(WEB_DOCUMENTS_LIST) || reference.contains(DOCUMENTS)) {
                JSONObject refJson = JSONObject.parseObject(reference);
                this.reference = refJson.getString(DOCUMENTS);
                this.webReference = refJson.getString(WEB_DOCUMENTS_LIST);
            }else {
                this.reference = reference;
                this.webReference = "[]";
            }
        }
    }
}
