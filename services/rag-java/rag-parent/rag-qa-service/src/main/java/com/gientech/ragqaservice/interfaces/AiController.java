package com.gientech.ragqaservice.interfaces;


import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import com.gientech.ragcommon.qa.dto.*;
import com.gientech.ragcommon.qa.request.*;
import com.gientech.ragqaservice.application.service.AiService;
import com.gientech.ragqaservice.interfaces.dto.RetrieveData;
import com.gientech.ragqaservice.interfaces.req.app.RetrieveDocReq4Platform;
import com.gientech.ragqaservice.interfaces.resp.RetrieveDoc;
import com.gientech.ragqaservice.application.service.AiService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import reactor.core.publisher.Flux;

import java.util.List;
import java.util.Map;
import java.util.Set;


/**
 * @author ws
 * @date 2024年06月01日 6:18 AM
 */
@Tag(name = "问答和引用")
@Slf4j
@RestController
@RequestMapping("/ai")
public class AiController {

    @Autowired
    private AiService aiService;

    /**
     * 检索召回接口和模型推理接口，返回接口拼接在一起
     *
     * @param aiRequest
     * @return
     */
    @Operation(summary = "检索召回接口和模型推理接口，返回接口拼接在一起")
    @PostMapping(value = "/question", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    @OperationLog(operateType = "用户问答")
    public Flux<ReplyDTO> question(@Validated @RequestBody AiRequest aiRequest) {
        aiService.assertAccessible(aiRequest);
        return aiService.question(aiRequest);
    }

    /**
     * 检索召回接口（检索文档）
     *
     * @param aiRequest
     * @return
     */
    @Operation(summary = "检索召回接口")
    @PostMapping(value = "/knowledge")
    public KnowledgeDTO knowledge(@Validated @RequestBody AiRequest aiRequest) {
        return aiService.knowledge(aiRequest);
    }


    /**
     * 检索召回接口和模型推理接口，返回结果未拼接
     *
     * @param aiRequest
     * @return
     */
    @Operation(summary = "检索召回接口和模型推理接口，返回结果未拼接")
    @PostMapping(value = "/question_re", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    @OperationLog(operateType = "用户问答")
    public Flux<ReplyDTO> questionRe(@Validated @RequestBody AiRequest aiRequest) {
        aiService.assertAccessible(aiRequest);
        return aiService.questionRe(aiRequest);
    }


    @Operation(summary = "AgentPlatform-检索召回接口")
    @PostMapping(value = "/retrieveDocs4Plat")
    @OperationLog(operateType = "用户问答")
    public RetrieveData retrieveDocs4Plat(@Validated @RequestBody RetrieveDocReq4Platform req4Platform) {
        return aiService.retrieveDocuments(req4Platform);
    }

    @Operation(summary = "并发批量问答,并返回对话接口")
    @PostMapping(value = "/question_res")
    @OperationLog(operateType = "并发批量问答")
    public DialogDTO questionRes(@Validated @RequestBody List<AiRequest> aiRequests) throws InterruptedException {
        return aiService.questionRes(aiRequests);
    }

    @Operation(summary = "知识检索召回测试,用于知识库问答的检测")
    @PostMapping(value = "/retrieveTecallTest", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    @OperationLog(operateType = "知识检索召回测试")
    public Flux<ReplyDTO> retrieveTecallTest(@Validated @RequestBody AiRequest aiRequest) {
        return aiService.retrieveTecallTest(aiRequest);
    }

    @Operation(summary = "问题推荐")
    @GetMapping(value = "/recommendQuestion")
    @OperationLog(operateType = "问题推荐")
    public String[] recommendQuestion(@RequestParam("queryId") String queryId,@RequestParam(value = "configId",required = false) Long configId) {
        return aiService.recommendQuestion(queryId,configId);
    }

    /**
     * 检索召回接口和模型推理接口，返回结果未拼接
     *
     * @param aiRequest
     * @return
     */
    @Operation(summary = "单文档问答接口")
    @PostMapping(value = "/questionForSingleDocument", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    @OperationLog(operateType = "单文档问答")
    public Flux<ReplyDTO> questionForSingleDocument(@Validated @RequestBody AiRequestForSingleDocument aiRequest) {
        return aiService.questionForSingleDocument(aiRequest);
    }

    /**
     * 获取可用的模型名称集合
     *
     * @return
     */
    @Operation(summary = "获取可用的模型名称集合")
    @GetMapping(value = "/getAiModelNames")
    public List<Map> getAiModelNames() {
        return aiService.getAiModelNames();
    }

//    @Operation(summary = "获取rerank的模型信息")
//    @GetMapping(value = "/getRerankModelInfos")
//    public List<RerankModelDTO> getRerankModelInfos() {
//        return aiService.getRerankModelInfos();
//    }

    /**
     * 通过一个语音文件解析文字
     *
     * @param file
     * @return
     */
    @Operation(summary = "minio地址存储和语音解析接口")
    @PostMapping("/audioUploadAndIdentify")
    public MinioAudioVTO audioUploadAndIdentify(@RequestParam("file") MultipartFile file) {
        if (file.isEmpty()) {
            throw new ApplicationException(ErrCodeEnum.NOT_AUDIO_EMPTY);
        }
        return aiService.audioUploadAndIdentify(file);
    }

    /**
     * 检索召回接口和模型推理接口，返回接口拼接在一起
     *
     * @param aiRequest
     * @return
     */
    @Operation(summary = "问答服务，浙商POC使用")
    @PostMapping(value = "/questionForCZBank")
    public String questionForCZBank(@Validated @RequestBody AiCZBankRequest aiRequest) {
        return aiService.questionForCZBank(aiRequest);
    }


    /**
     * 新增（或更新）问答内容接口
     *
     * @param questionAndAnswerAddReq
     * @return
     */
    @Operation(summary = "新增（或更新）问答内容接口")
    @PostMapping(value = "/addOrUpdateQA")
    public Boolean addOrUpdateQuestionAndAnswer(@Validated @RequestBody QuestionAndAnswerAddReq questionAndAnswerAddReq) {
        return aiService.addOrUpdateQuestionAndAnswer(questionAndAnswerAddReq);
    }

    @Operation(summary = "统一搜索接口")
    @PostMapping(value = "/commonSearch", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    @OperationLog(operateType = "统一搜索")
    public Flux<ReplyDTO> commonSearch(@Validated @RequestBody CommonSearchRequest searchRequest) {
        Flux<ReplyDTO> replyResult = aiService.commonSearch(searchRequest);
        return replyResult;
    }

    @Operation(summary = "添加统一搜索记录")
    @PostMapping(value = "/addQuery")
    public void addQuery(@RequestParam("queryContent") String queryContent) {
        aiService.addQuery(queryContent);
    }

    @Operation(summary = "获取统一搜索记录")
    @PostMapping(value = "/getQueryHistory")
    public Set<Object> getQueryHistory() {
        return aiService.getQueryHistory();
    }

    @Operation(summary = "删除统一搜索记录")
    @DeleteMapping(value = "/delQueryHistory")
    public Boolean delQueryHistory(@RequestParam(value = "queryContent", required = false) String queryContent) {
        return aiService.delQueryHistory(queryContent);
    }
}
