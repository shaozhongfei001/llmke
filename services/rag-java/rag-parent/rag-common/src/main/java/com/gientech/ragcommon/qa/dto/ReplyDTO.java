package com.gientech.ragcommon.qa.dto;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.nacos.shaded.com.google.common.collect.Lists;
import com.alibaba.nacos.shaded.com.google.common.collect.Maps;
import com.gientech.ragcommon.qa.enmus.AIResultTypeEnum;
import com.gientech.ragcommon.qa.enmus.LlmTypeEnums;
import com.gientech.ragcommon.qa.enmus.ReplyStatusEnums;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import org.apache.commons.lang3.StringUtils;
import org.springframework.util.CollectionUtils;
import reactor.core.publisher.Flux;

import java.time.Duration;
import java.util.*;

import static com.gientech.ragcommon.qa.constant.AIConstant.DOCUMENTS;
import static com.gientech.ragcommon.qa.constant.AIConstant.WEB_DOCUMENTS_LIST;

/**
 * @Descrption:
 * @Author:ws
 * @Date:2024/06/04 09:36
 **/
@Schema(name = "提问响应体")
@Data
public class ReplyDTO {

    @Schema(name = "sessionId", description = "会话id")
    private String sessionId;

    /**
     * 问题ID
     */
    @Schema(name = "queryId", description = "提问id")
    private String queryId;


    /**
     * 问题提交时间
     */
    @Schema(name = "lastDate", description = "问题提交时间")
    private Date lastDate;

    /**
     * 1.进行中，2.结束，3.异常
     */
    @Schema(name = "status", description = "答案类型体：1.进行中，2.结束，3.异常")
    private ReplyStatusEnums status;

    @Schema(name = "reply", description = "答案内容")
    private ReplyContentDTO reply;

    @Schema(name = "reference", description = "召回文档")
    private String reference;

    @Schema(name = "webReference", description = "联网召回文档")
    private String webReference;

    @Schema(name = "databaseReference", description = "数据库召回数据")
    private String databaseReference;

    @Schema(name = "docsTree", description = "召回文档(树状结构)")
    private String docsTree;

    @Schema(name = "resultType", description = "响应的类型 1:正常大模型推理; 2:FAQ; 3 命中敏感词;4 强知识依赖;5文档上传问答")
    private Integer resultType;

    @Schema(name = "filePaths", description = "文件路径(文档上传问答所用的文件路径)")
    private String filePaths;

    @Schema(name = "respTime", description = "接口响应时间(毫秒)")
    private Long respTime;

    @Schema(name = "tokens", description = "tokens数量")
    private Integer tokens = 0;

    @Schema(name = "promptContent", description = "prompt数据")
    private String promptContent;

//    public Long getRespTime() {
//        return Objects.isNull(respTime) ? null : (respTime / 1000);
//    }

    @Schema(name = "llmType", description = "推理类型 1:推理接口, 2:表格推理接口 默认值1")
    private Integer llmType = LlmTypeEnums.LLM_NORMAL.getCode();


    public static Flux<ReplyDTO> fastReplyRe(String sessionId, String queryId, String content, List<Document> webRsDocuments) {
        return Flux.just(fastBuildReplyRe(sessionId, queryId, content,webRsDocuments,AIResultTypeEnum.LLM.getCode(), null)).delayElements(Duration.ofSeconds(0));
    }

    public static Flux<ReplyDTO> fastReplyRe(String sessionId, String queryId, String content, List<Document> webRsDocuments,Integer resultType,Long respTime) {
        return Flux.just(fastBuildReplyRe(sessionId, queryId, content,webRsDocuments,resultType,respTime)).delayElements(Duration.ofSeconds(0));
    }

    public static Flux<ReplyDTO> fastRepseRe(String sessionId, String queryId, String content, String docs,Integer resultType,Long respTime) {
        return Flux.just(fastBuildRepseRe(sessionId, queryId, content,docs,resultType,respTime)).delayElements(Duration.ofSeconds(0));
    }

    public static Flux<ReplyDTO> fastReplyRe(String sessionId, String queryId, String content, List<Document> webRsDocuments,Integer resultType) {
        return Flux.just(fastBuildReplyRe(sessionId, queryId, content,webRsDocuments,resultType,null)).delayElements(Duration.ofSeconds(0));
    }

    public static Flux<ReplyDTO> fastReply(String sessionId, String queryId, String content, List<Map<String,Object>> webRsDocuments) {
        return Flux.just(fastBuildReply(sessionId, queryId, content,webRsDocuments)).delayElements(Duration.ofSeconds(0));
    }

    public static ReplyDTO fastBuildRepseRe(String sessionId, String queryId, String content, String docs,Integer resultType,Long respTime) {
        ReplyDTO replyDTO = new ReplyDTO();
        replyDTO.setSessionId(sessionId);
        replyDTO.setQueryId(queryId);
        replyDTO.setLastDate(new Date());
        replyDTO.setReference(docs);
        replyDTO.setStatus(ReplyStatusEnums.PARSE_SUCCESS);
        ReplyContentDTO replyContentDTO = new ReplyContentDTO();
        replyContentDTO.setContent(content);
        replyDTO.setReply(replyContentDTO);
        replyDTO.setResultType(resultType);
        replyDTO.setRespTime(respTime);
        return replyDTO;
    }

    public static ReplyDTO fastBuildReplyRe(String sessionId, String queryId, String content, List<Document> webRsDocuments,Integer resultType,Long respTime) {
        ReplyDTO replyDTO = new ReplyDTO();
        replyDTO.setSessionId(sessionId);
        replyDTO.setQueryId(queryId);
        replyDTO.setLastDate(new Date());
        if(Objects.nonNull(webRsDocuments)){
            String docs = JSON.toJSONString(webRsDocuments);
            replyDTO.setReference(docs);
        }
        replyDTO.setStatus(ReplyStatusEnums.PARSE_SUCCESS);
        ReplyContentDTO replyContentDTO = new ReplyContentDTO();
        replyContentDTO.setContent(content);
        replyDTO.setReply(replyContentDTO);
        replyDTO.setResultType(resultType);
        replyDTO.setRespTime(respTime);
        return replyDTO;
    }

    public static ReplyDTO fastBuildReply(String sessionId, String queryId, String content,List<Map<String,Object>> webRsDocuments) {
        ReplyDTO replyDTO = new ReplyDTO();
        replyDTO.setSessionId(sessionId);
        replyDTO.setQueryId(queryId);
        replyDTO.setLastDate(new Date());
        if(Objects.nonNull(webRsDocuments)){
            String docs = JSON.toJSONString(webRsDocuments);
            replyDTO.setReference(docs);
        }
        replyDTO.setStatus(ReplyStatusEnums.PARSE_SUCCESS);
        ReplyContentDTO replyContentDTO = new ReplyContentDTO();
        replyContentDTO.setContent(content);
        replyDTO.setReply(replyContentDTO);
        return replyDTO;
    }

    public void setDocsTree(String docs) {
        if(StringUtils.isNotEmpty(docs)){
            Map<String,List<Document>> docMap = Maps.newHashMap();
            List<Document> documents = JSON.parseArray(docs, Document.class);
            documents.forEach(document -> {
                String parsedFilePath = document.getParsedFilePath();
                List<Document> documentList = docMap.get(parsedFilePath);
                if(CollectionUtils.isEmpty(documentList)){
                    documentList = Lists.newLinkedList();
                    docMap.put(parsedFilePath,documentList);
                }
                documentList.add(document);
            });
            this.docsTree = JSON.toJSONString(docMap);
        }
    }

    public void setReference(String reference) {
        if(StringUtils.isNotEmpty(reference)){
            if (reference.contains(WEB_DOCUMENTS_LIST) || reference.contains(DOCUMENTS)) {
                JSONObject refJson = JSONObject.parseObject(reference);
                this.reference = refJson.getString(DOCUMENTS);
                this.webReference = refJson.getString(WEB_DOCUMENTS_LIST);
            }else{
                this.reference = reference;
                this.webReference = "[]";
            }
        }
    }
}
