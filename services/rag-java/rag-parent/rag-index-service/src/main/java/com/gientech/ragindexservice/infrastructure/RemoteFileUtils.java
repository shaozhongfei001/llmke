package com.gientech.ragindexservice.infrastructure;

import com.alibaba.fastjson2.JSONObject;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragcommon.infrastructure.exception.DomainException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.http.*;
import org.springframework.retry.annotation.Backoff;
import org.springframework.retry.annotation.Recover;
import org.springframework.retry.annotation.Retryable;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;

import java.util.Objects;

@Slf4j
@Component
@RefreshScope
public class RemoteFileUtils {


    private final RestTemplate restTemplate;

    public RemoteFileUtils(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    /**
     * 获取文件的修订时间
     */
    @Value("${remote.file-revise_date.url}")
    private String remoteFilereviseDateUrl;


    /**
     * 文件解析接口（异步）
     */
    @Value("${remote.file-parse.url}")
    private String remoteFileParseUrl;

    /**
     * 文件解析接口(同步)
     */
    @Value("${remote.file-parse-sync.url}")
    private String remoteFileParseSyncUrl;

    /**
     * 删除知识库知识库指定文件索引
     */
    @Value("${remote.del-index-file.url}")
    private String remoteDelIndexFileUrl;

    /**
     * 删除知识库索引
     */
    @Value("${remote.del-index.url}")
    private String remoteDelIndexUrl;

    /**
     * 删除知识库向量数据&删除知识库知识库指定向量数据&删除faq
     */
    @Value("${remote.del-vector.url}")
    private String remoteDelvectorUrl;

    /**
     * 抽取问答对
     */
    @Value("${remote.faq-extract.url}")
    private String remoteFaqExtractUrl;

    /**
     * 保存问答对
     */
    @Value("${remote.faq-sava.url}")
    private String remoteFaqSavaUrl;

    /**
     * 更新问答对
     */
    @Value("${remote.faq-update.url}")
    private String remoteFaqUpdateUrl;

    /**
     * 查询问答对列表
     */
    @Value("${remote.faq-list.url}")
    private String remoteFaqListUrl;

    /**
     * 查询问答对数量
     */
    @Value("${remote.faq-count.url}")
    private String remoteFaqCountUrl;

    /**
     * 查询问答对数量
     */
    @Value("${remote.faq-page-list.url}")
    private String remoteFaqPageListUrl;

    /**
     * 保存问答对(es)
     */
    @Value("${remote.faq-sava-es.url}")
    private String remoteFaqSaveEsUrl;

    /**
     * 更新问答对(es)
     */
    @Value("${remote.faq-update-es.url}")
    private String remoteFaqUpdateEsUrl;

    /**
     * 删除问答对(es)
     */
    @Value("${remote.faq-delete-es.url}")
    private String remoteFaqDeleteEsUrl;

    /**
     * 查询问答对(分页 es)
     */
    @Value("${remote.faq-page-list-es.url}")
    private String remoteFaqPageListEsUrl;

    /**
     * 更新FAQ字段(milvus)
     */
    @Value("${remote.faq-update-field.url}")
    private String remoteFaqUpdateFieldUrl;

    /**
     * faq润色接口
     */
    @Value("${remote.faq-polish.url}")
    private String remoteFaqPolishUrl;

    /**
     * faq相似问生成
     */
    @Value("${remote.faq-simi-question.url}")
    private String remoteFaqSimiQuestionUrl;

    /**
     * 更新FAQ字段(es)
     */
    @Value("${remote.faq-update-field-es.url}")
    private String remoteFaqUpdateFieldteEsUrl;

    /**
     * 检测模型是否可用
     */
    @Value("${remote.model-check.url}")
    private String remoteModelCheckUrl;


    @Value("${remote.file-multi-version.url}")
    private String fileMultiVersionUrl;


    public String fileMultiVersion(String requestPara) {
        return doExchange(requestPara, fileMultiVersionUrl, HttpMethod.POST).getBody();
    }

    public String faqSimiQuestion(String requestPara) {
        return doExchange(requestPara, remoteFaqSimiQuestionUrl, HttpMethod.POST).getBody();
    }

    public String faqPolish(String requestPara) {
        return doExchange(requestPara, remoteFaqPolishUrl, HttpMethod.POST).getBody();
    }

    public String updateFieldteEs(String requestPara) {
        return doExchange(requestPara, remoteFaqUpdateFieldteEsUrl, HttpMethod.POST).getBody();
    }

    public String pageListEs(String requestPara) {
        return doExchange(requestPara, remoteFaqPageListEsUrl, HttpMethod.POST).getBody();
    }

    public String faqDelEs(String requestPara) {
        return doExchange(requestPara, remoteFaqDeleteEsUrl, HttpMethod.POST).getBody();
    }

    public String faqUpdateEs(String requestPara) {
        return doExchange(requestPara, remoteFaqUpdateEsUrl, HttpMethod.POST).getBody();
    }

    public String faqSaveEs(String requestPara) {
        return doExchange(requestPara, remoteFaqSaveEsUrl, HttpMethod.POST).getBody();
    }

    public String faqPageList(String requestPara) {
        return doExchange(requestPara, remoteFaqPageListUrl, HttpMethod.POST).getBody();
    }

    public String faqCount(String requestPara) {
        return doExchange(requestPara, remoteFaqCountUrl, HttpMethod.POST).getBody();
    }

    public String faqExtract(String requestPara) {
        return doExchange(requestPara, remoteFaqExtractUrl, HttpMethod.POST).getBody();
    }

    public String faqList(String requestPara) {
        return doExchange(requestPara, remoteFaqListUrl, HttpMethod.POST).getBody();
    }


    @Async("fileProcessExecutor")
    @Retryable(retryFor = Exception.class, maxAttempts = 4, backoff = @Backoff(delay = 3000))
    public void faqUpdateField(String requestPara) {
        String resp = doExchange(requestPara, remoteFaqUpdateFieldUrl, HttpMethod.POST).getBody();
        JSONObject respJson = JSONObject.parseObject(resp);
        if (!Objects.equals(respJson.getInteger("code"), 200))
            throw new ApplicationException(ErrCodeEnum.FAQ_UPDATE_ERROR.getErrCode(), getErrorMsg(respJson, requestPara));
    }

    @Async("fileProcessExecutor")
    @Retryable(retryFor = Exception.class, maxAttempts = 4, backoff = @Backoff(delay = 3000))
    public void faqUpdate(String requestPara) {
        String resp = doExchange(requestPara, remoteFaqUpdateUrl, HttpMethod.POST).getBody();
        JSONObject respJson = JSONObject.parseObject(resp);
        if (!Objects.equals(respJson.getInteger("code"), 200))
            throw new ApplicationException(ErrCodeEnum.FAQ_UPDATE_ERROR.getErrCode(), getErrorMsg(respJson, requestPara));
    }

    @Async("fileProcessExecutor")
    @Retryable(retryFor = Exception.class, maxAttempts = 4, backoff = @Backoff(delay = 3000))
    public void faqSave(String requestPara) {
        String resp = doExchange(requestPara, remoteFaqSavaUrl, HttpMethod.POST).getBody();
        JSONObject respJson = JSONObject.parseObject(resp);
        if (!Objects.equals(respJson.getInteger("code"), 200))
            //FIXME 是否应该记录失败时间、原因到异步任务日志表中
            throw new ApplicationException(ErrCodeEnum.FAQ_SAVE_ERROR.getErrCode(), getErrorMsg(respJson, requestPara));
    }

    private String getErrorMsg(JSONObject respJson, String requestPara) {
        return respJson.getString("msg") + ",入参为：" + requestPara;
    }

    /**
     * 删除miluvs中的表
     *
     * @param tableName
     */
    @Async("fileProcessExecutor")
    @Retryable(retryFor = Exception.class, maxAttempts = 4, backoff = @Backoff(delay = 3000))
    public void deleteMiluvsTable(String tableName) {
        JSONObject delParam = new JSONObject();
        delParam.put("collection_name", tableName);
        String resp = doExchange(JSONObject.toJSONString(delParam), remoteDelvectorUrl, HttpMethod.POST).getBody();
        JSONObject respJson = JSONObject.parseObject(resp);
        if (respJson.getInteger("code").equals(500)) {
            return;
        }
        if (!Objects.equals(respJson.getInteger("code"), 200)) {
            throw new ApplicationException(ErrCodeEnum.FAQ_DELETE_ERROR.getErrCode(), getErrorMsg(respJson, tableName));
        }
    }

    /**
     * 删除es中的表
     *
     * @param tableName
     */
    @Async("fileProcessExecutor")
    @Retryable(retryFor = Exception.class, maxAttempts = 4, backoff = @Backoff(delay = 3000))
    public void deleteEsTable(String tableName) {
        JSONObject param = new JSONObject();
        param.put("index_name", tableName);
        String resultStr = doExchange(JSONObject.toJSONString(param), remoteDelIndexUrl, HttpMethod.POST).getBody();
        JSONObject result = JSONObject.parseObject(resultStr);
        if (result.getInteger("code").equals(500)) {
            log.warn("数据不存在");
            return;
        }
        if (!result.getInteger("code").equals(200)) {
            throw new ApplicationException(ErrCodeEnum.DELETE_INDEX_ERROR.getErrCode(), getErrorMsg(result, tableName));
        }
    }

    @Async("fileProcessExecutor")
    @Retryable(retryFor = Exception.class, maxAttempts = 4, backoff = @Backoff(delay = 3000))
    public void faqDel(String requestPara) {
        String resp = doExchange(requestPara, remoteDelvectorUrl, HttpMethod.POST).getBody();
        JSONObject respJson = JSONObject.parseObject(resp);
        if (respJson.getInteger("code").equals(500)) {
            return;
        }
        if (!Objects.equals(respJson.getInteger("code"), 200)) {
            throw new ApplicationException(ErrCodeEnum.FAQ_DELETE_ERROR.getErrCode(), getErrorMsg(respJson, requestPara));
        }
    }

    @Async("fileProcessExecutor")
    @Retryable(retryFor = Exception.class, maxAttempts = 4, backoff = @Backoff(delay = 3000))
    public void delDelvector(String requestPara) {
        String resp = doExchange(requestPara, remoteDelvectorUrl, HttpMethod.POST).getBody();
        JSONObject respJson = JSONObject.parseObject(resp);
        if (respJson.getInteger("code").equals(500)) {
            log.warn("数据不存在");
            return;
        }
        if (!Objects.equals(respJson.getInteger("code"), 200))
            throw new DomainException(ErrCodeEnum.DELETE_INDEX_ERROR);
    }

    @Async("fileProcessExecutor")
    @Retryable(retryFor = Exception.class, maxAttempts = 4, backoff = @Backoff(delay = 3000))
    public void delIndex(String kbName) {
        JSONObject param = new JSONObject();
        param.put("index_name", kbName);
        String resultStr = doExchange(JSONObject.toJSONString(param), remoteDelIndexUrl, HttpMethod.POST).getBody();
        JSONObject result = JSONObject.parseObject(resultStr);
        if (result.getInteger("code").equals(500)) {
            log.warn("数据不存在");
            return;
        }
        if (!result.getInteger("code").equals(200)) {
            throw new ApplicationException(ErrCodeEnum.DELETE_INDEX_ERROR.getErrCode(), getErrorMsg(result, kbName));
        }
    }

    //    @Async("asyncExecutor")
//    @Retryable(value = ApplicationException.class, maxAttempts = 4, backoff = @Backoff(delay = 3000))
    public String delIndexFiles(String requestPara) {
        return doExchange(requestPara, remoteDelIndexFileUrl, HttpMethod.POST).getBody();
    }

//    @Retryable(
//            retryFor = {Exception.class},
//            maxAttempts = 3,
//            backoff = @Backoff(delay = 10000))
    public String fileParse(String requestPara) {
        return doExchange(requestPara, remoteFileParseUrl, HttpMethod.POST).getBody();
    }

    public String fileSyncParse(String requestPara) {
        return doExchange(requestPara, remoteFileParseSyncUrl, HttpMethod.POST).getBody();
    }

    @Recover
    public String recover(ResourceAccessException e) {
        throw new ApplicationException(ErrCodeEnum.RETRY_ERROR);
    }

    public String filereviseDate(String requestPara) {
        return doExchange(requestPara, remoteFilereviseDateUrl, HttpMethod.POST).getBody();
    }

    public String getChunkByDocumentId(String requestPara) {
        return doExchange(requestPara, remoteFaqPageListUrl, HttpMethod.POST).getBody();
    }

    public String modelCheck(String requestPara) {
        log.info("开始远程调用检测模型可用性接口,URL:{},请求方式:{},入参:{}", remoteModelCheckUrl, "POST", requestPara);
        String body;
        try {
            body = doExchange(requestPara, remoteModelCheckUrl, HttpMethod.POST).getBody();
        } catch (Exception e) {
            log.error("远程调用检测模型可用性接口失败", e);
            throw new ApplicationException(ErrCodeEnum.MODEL_CHECK_FAIL);
        }
        return body;
    }


    private ResponseEntity<String> doExchange(String param, String url, HttpMethod httpMethod) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Object> requestEntity = new HttpEntity<>(param, headers);
        log.info("远程url:{},请求方式:{},请求参数:{}", url, httpMethod.name(), param);
        ResponseEntity<String> response = restTemplate.exchange(url, httpMethod, requestEntity, String.class);
        log.info("远程url:{},响应结果:{}", url, JSONObject.toJSONString(response.getBody()));
        HttpStatusCode httpStatusCode = response.getStatusCode();
        if (200 != httpStatusCode.value()) {
            throw new ApplicationException(ErrCodeEnum.FILE_PARSE_ERROR);
        }
        return response;
    }
}
