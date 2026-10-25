package com.gientech.ragqaservice.application.service;

import com.gientech.ragcommon.qa.dto.*;
import com.gientech.ragcommon.qa.request.*;
import com.gientech.ragqaservice.interfaces.req.app.RetrieveDocReq;
import com.gientech.ragqaservice.interfaces.dto.RetrieveData;
import com.gientech.ragqaservice.interfaces.req.app.RetrieveDocReq4Platform;
import com.gientech.ragqaservice.interfaces.resp.RetrieveDoc;
import org.springframework.web.multipart.MultipartFile;
import reactor.core.publisher.Flux;

import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * <p>
 * 知识库明细 服务类
 * </p>
 *
 * @author wudf
 * @since 2024-06-04
 */
public interface AiService {

    /**
     * @param aiRequest
     * @return
     */
    /**
     * R13-SEC-A1：问答入口的同步鉴权（在建立 SSE 流之前完成），
     * 保证越权请求得到明确的 403/30016，而不是被包成"模型暂时无法返回"。
     */
    void assertAccessible(AiRequest aiRequest);

    Flux<ReplyDTO> question(AiRequest aiRequest);

    /**
     * @param aiRequest
     * @return
     */
    String questionForCZBank(AiCZBankRequest aiRequest);

    /**
     * @param aiRequest
     * @return
     */
    KnowledgeDTO knowledge(AiRequest aiRequest);


    /**
     * 检索大模型推理接口
     *
     * @param aiRequest
     * @return
     */
    Flux<ReplyDTO> questionRe(AiRequest aiRequest);


    String[] recommendQuestion(String queryId,Long configId);


    /**
     * 检索大模型推理接口
     *
     * @param aiRequest
     * @return
     */
    Flux<ReplyDTO> questionForSingleDocument(AiRequestForSingleDocument aiRequest);

    /**
     * @return
     */
    List<Map> getAiModelNames();


    /**
     * @param file
     * @return
     */
    MinioAudioVTO audioUploadAndIdentify(MultipartFile file);

    /**
     * 新增（或更新）问答内容
     *
     * @param questionAndAnswerAddReq
     * @return
     */
    Boolean addOrUpdateQuestionAndAnswer(QuestionAndAnswerAddReq questionAndAnswerAddReq);

    /**
     * 检索大模型推理接口
     *
     * @param searchRequest
     * @return
     */
    Flux<ReplyDTO> commonSearch(CommonSearchRequest searchRequest);

    void addQuery(String queryContent);

    Set<Object> getQueryHistory();

    Boolean delQueryHistory(String queryContent);

    /**
     * 知识检索召回测试
     * @param aiRequest
     * @return
     */
    Flux<ReplyDTO> retrieveTecallTest(AiRequest aiRequest);

    /**
     * 获取rerank的模型信息
     * @return
     */
//    List<RerankModelDTO> getRerankModelInfos();

    /**
     * 批量调用接口
     * @param aiRequests
     * @return
     */
    DialogDTO questionRes(List<AiRequest> aiRequests) throws InterruptedException;


    RetrieveData retrieveDocuments(RetrieveDocReq4Platform req4Platform);
}
