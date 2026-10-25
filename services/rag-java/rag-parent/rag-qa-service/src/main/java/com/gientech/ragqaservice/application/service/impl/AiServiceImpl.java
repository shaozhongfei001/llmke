package com.gientech.ragqaservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.util.ArrayUtil;
import cn.hutool.core.util.StrUtil;
import cn.hutool.db.Entity;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.fasterxml.jackson.databind.JsonNode;
import com.gientech.ragcommon.auth.dto.UserInfoDTO;
import com.gientech.ragcommon.auth.enums.PrivilegeTypeEnums;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.constant.IndexConstant;
import com.gientech.ragcommon.index.dto.*;
import com.gientech.ragcommon.index.dto.tools.TLDatabaseDTO;
import com.gientech.ragcommon.index.dto.tools.TLTableDataDto;
import com.gientech.ragcommon.index.dto.tools.TLTableDto;
import com.gientech.ragcommon.index.enmus.DataSourceTypeEnum;
import com.gientech.ragcommon.index.request.PageFileStreamReq;
import com.gientech.ragcommon.index.request.QueryDataReq;
import com.gientech.ragcommon.index.utils.JSONPagination;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragcommon.infrastructure.utils.AesEncryptUtil;
import com.gientech.ragcommon.infrastructure.utils.MarkdownUtils;
import com.gientech.ragcommon.infrastructure.utils.PdfUtils;
import com.gientech.ragcommon.infrastructure.utils.ReadRemoteFileUtils;
import com.gientech.ragcommon.qa.constant.QaConstant;
import com.gientech.ragcommon.qa.dto.*;
import com.gientech.ragcommon.qa.enmus.AIResultTypeEnum;
import com.gientech.ragcommon.qa.enmus.ReplyStatusEnums;
import com.gientech.ragcommon.qa.enmus.StatusEnums;
import com.gientech.ragcommon.qa.enmus.SysTypeEnums;
import com.gientech.ragcommon.qa.entity.Config;
import com.gientech.ragcommon.qa.request.*;
import com.gientech.ragcommon.sensitive.dto.SensitiveWordsDTO;
import com.gientech.ragcommon.sensitive.utils.AnsjParseWordUtils;
import com.gientech.ragqaservice.application.convertor.RetrieveDocReqConvertor;
import com.gientech.ragqaservice.application.remote.*;
import com.gientech.ragqaservice.application.service.AiService;
import com.gientech.ragqaservice.application.service.DialogueAppService;
import com.gientech.ragqaservice.application.service.entity.AiHistory;
import com.gientech.ragqaservice.application.service.entity.QuestionRecommendRequest;
import com.gientech.ragqaservice.application.service.entity.QuestionRewriteReq;
import com.gientech.ragqaservice.application.service.entity.SqlGenerateRequest;
import com.gientech.ragqaservice.domain.conventer.DialogueConvertor;
import com.gientech.ragqaservice.domain.conventer.QuestionConvertor;
import com.gientech.ragqaservice.domain.entity.*;
import com.gientech.ragqaservice.domain.service.*;
import com.gientech.ragqaservice.infrastructure.HttpUtils;
import com.gientech.ragqaservice.infrastructure.NacosConfig;
import com.gientech.ragqaservice.interfaces.dto.RetrieveData;
import com.gientech.ragqaservice.interfaces.req.app.RetrieveDocReq;
import com.gientech.ragqaservice.interfaces.req.app.RetrieveDocReq4Platform;
import com.gientech.ragqaservice.interfaces.resp.*;
import com.gientech.start.redisson.utils.RedissonUtils;
import com.gientech.start.storage.exception.FileStorageException;
import com.gientech.start.storage.model.FileInfo;
import com.gientech.start.storage.properties.StorageProperties;
import com.gientech.start.storage.utils.FileStorageUtils;
import com.google.common.collect.Lists;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.apache.skywalking.apm.toolkit.trace.Trace;
import org.reactivestreams.Publisher;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.task.TaskExecutor;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.reactive.function.BodyInserters;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Duration;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

import static com.gientech.ragcommon.infrastructure.emuns.RedisKeyEnums.USER_SEARCH_PREFIX;
import static com.gientech.ragcommon.qa.constant.AIConstant.*;


/**
 * <p>
 * 知识库 服务类
 * </p>
 *
 * @author wudf
 * @since 2024-06-04
 */
@Slf4j
@Service
public class AiServiceImpl implements AiService {

    @Autowired
    @Qualifier("webLlmOpenChatClient")
    private WebClient webLlmOpenChatClient;

    @Autowired
    private DialogueDomainService dialogueDomainService;

    @Autowired
    private QuestionDomainService questionDomainService;

    @Autowired
    private AnswerDomainService answerDomainService;

    @Autowired
    private SearchConfigDomainService searchConfigDomainService;

    @Autowired
    public NacosConfig nacosConfig;

    @Autowired
    @Qualifier("restTemplate")
    public RestTemplate restTemplate;

    @Autowired
    private AuthClient authClient;

    @Autowired
    private SensitiveWordsClient sensitiveWordsClient;

    @Autowired
    private FileStorageUtils fileStorageUtils;

    @Autowired
    private StorageProperties storageProperties;

    @Autowired
    private RedissonUtils redissonUtils;

    @Autowired
    private KbClient kbClient;

    @Autowired
    private ModelClient modelClient;

    @Autowired
    private LlmClient llmClient;

    @Autowired
    private RetrieveClient retrieveClient;

    @Autowired
    @Qualifier("asyncExecutor")
    private TaskExecutor asyncExecutor;

    @Autowired
    private ApiKeyInfoDomainService apiKeyInfoDomainService;

    @Autowired
    private AesEncryptUtil aesEncryptUtil;

    @Autowired
    private DialogueAppService dialogueAppService;

    private static ExecutorService executorService = Executors.newFixedThreadPool(Runtime.getRuntime().availableProcessors() * 4 + Runtime.getRuntime().availableProcessors() / 2);

    @Value("${server.host-ip}")
    private String serverHostIp;

    @Value("${server.port}")
    private String serverPort;

    @Autowired
    private AnsjParseWordUtils ansjParseWordUtils;

    //文件过期时间
    private static final Long FILE_EXPIRE_TIME = 60 * 60 * 8L;
    //知识检索召回测试接口请求开始时间
    private Long llmChatRequstTime = null;
    //prompt组装结果
    private String promptContent = null;


    public enum InputType {
        /**
         * 拼接输出
         */
        MONTAGE,
        /**
         * 分离输出
         */
        SEPARATE;

    }

    @Override
    public void assertAccessible(AiRequest aiRequest) {
        Config config = null;
        try {
            if (StringUtils.isNotBlank(aiRequest.getSessionId())) {
                Dialogue dialogue = dialogueDomainService.getDialogueBySessionId(aiRequest.getSessionId());
                config = dialogue == null ? null : dialogue.getConfig();
            }
            if (config == null && aiRequest.getConfigId() != null) {
                config = searchConfigDomainService.getConfigById(aiRequest.getConfigId());
            }
        } catch (Exception ex) {
            log.warn("resolve config for access check failed: {}", ex.getMessage());
        }
        assertKnowledgeBaseReadable(config);
    }

    @Override
    public Flux<ReplyDTO> question(AiRequest aiRequest) {
        log.info("questionRequest:" + aiRequest.toString());
        return publicQuestion(aiRequest, InputType.MONTAGE);
    }


    @Override
    public String questionForCZBank(AiCZBankRequest aiRequest) {
        return publicQuestionForCZBank(aiRequest, InputType.MONTAGE);
    }

    private Flux<ReplyDTO> publicQuestionRe(AiRequest aiRequest, InputType inputType) {
        String sessionId = aiRequest.getSessionId();
        String queryId = aiRequest.getQueryId();
        Long dialogueId = null;
        try {
            Boolean enableThinking = aiRequest.getEnableThinking();
            Boolean enableWebsearch = aiRequest.getEnableWebsearch();
            llmChatRequstTime = System.currentTimeMillis();
            //保存对话&助手配置
            dialogueId = saveOrUpdateDialogue(aiRequest);
            sessionId = aiRequest.getSessionId();
            queryId = aiRequest.getQueryId();

            Dialogue dialogue = dialogueDomainService.getDialogueById(dialogueId);
            Config config = dialogue.getConfig();
            // R13-SEC-A1（问答主链）：配置有权限 ≠ 配置指向的知识库有权限；此处做对象级校验
            assertKnowledgeBaseReadable(config);

            String query = aiRequest.getContent();
            //问题改写
            String reWriteContent = questionRewrite(dialogueId, query, config);

            ExtendedConfig extendedConfig = new ExtendedConfig();
            //查询模型配置、设置推理思考参数
            buildConfig(config, enableThinking, enableWebsearch);
            // 检索召回+推理（解决流式问题）
            // 敏感词
            List<SensitiveWordsDTO> sensWordList;
            //助手拓展配置
            ExtendedConfig alParams;
            //表格筛选返回的结果
            List<Document> tableSelectedDocuments = null;
            //知识库召回的数据
            List<Document> webRsDocuments = new ArrayList<>();
            //联网问答召回的数据
            List<WebDocument> webDocumentList = null;
            RetrievedData retrievedData = null;
            SqlMetaData sqlMetaData = null;
            //文档上传问答(可以查询到文件就是文档上传问答)
            List<KnowledgeBaseFileDTO> files = kbClient.getByKbNameAndUid(sessionId, aiRequest.getFileUids());
            //类型转换
            List<FilePathDTO> filePathDTOS = convertToFilePathDTOS(files);

            //组装请求参数
            extendedConfig.init(config.getConfigJson());
            extendedConfig.setQuery(query);
            extendedConfig.setRewrittenQuery(reWriteContent);
            //获取敏感词
            sensWordList = getSensitiveWordsByIds(config.getSensitiveWordIds());
            log.info("sensitive words are {}", JSON.toJSONString(sensWordList));
            //对问题进行分词，如果有敏感词，则直接返回通用回答
            if (matchSensWord(sensWordList, aiRequest.getContent()).isPresent()) {
                String answer = config.getDefaultAnswer();
                //保存问题和答案
                Long repseTime = System.currentTimeMillis() - llmChatRequstTime;
                addQuestionAndAnswerRe(null, dialogueId, aiRequest, answer, "[]", AIResultTypeEnum.SENSITIVE_WORDS.getCode(), repseTime);
                //如果问题命中敏感词，则返回配置的默认回复
                return ReplyDTO.fastReplyRe(sessionId, queryId, answer, Lists.newArrayList(), AIResultTypeEnum.SENSITIVE_WORDS.getCode(), repseTime);
            }

            //检索召回组装json数据
            alParams = retrieveRecallParamToJson(extendedConfig);
            CompletableFuture<RetrieveSqlDataReference> retrieveSqlFuture = null;
            //知识库不为空且文件为空是正常的问答接口,需要先调召回接口 (文档上传问答不需要调召回接口)
            if (Objects.nonNull(extendedConfig.getKnowledgeBaseName()) && CollectionUtils.isEmpty(files)) {
                //1.调用检索召回接口
                retrievedData = retrieveRecall(aiRequest, alParams, dialogueId, Boolean.FALSE);
                if (Objects.nonNull(retrievedData)) {
                    //召回sql
//                retrieveSqlFuture = retrieveSqlData(config, aiRequest.getContent(), dialogueId, retrievedData);
                    sqlMetaData = retrieveSqlData(config, aiRequest.getContent(), dialogueId, retrievedData);

                    List<Document> fullDocuments = retrievedData.getDocuments(storageProperties.getDefaultStorageProperties().getEndPoint());
                    tableSelectedDocuments = retrievedData.getTableSelectedDocuments(storageProperties.getDefaultStorageProperties().getEndPoint());
                    webDocumentList = retrievedData.getWebDocumentList();
                    webRsDocuments.addAll(fullDocuments);
                    webRsDocuments.addAll(tableSelectedDocuments);

                    List<Faq> faqs = retrievedData.getFaqs();
                    //开启FAQ,走以下逻辑
                    if (!CollectionUtils.isEmpty(faqs)) {
                        //faq筛选
                        Long repseTime = System.currentTimeMillis() - llmChatRequstTime;
                        String answer = faqSelect(dialogueId, aiRequest, faqs, extendedConfig);
                        addQuestionAndAnswerRe(alParams, dialogueId, aiRequest, answer, "[]", AIResultTypeEnum.FAQ.getCode(), repseTime);
                        if (StringUtils.isNotEmpty(answer)) {
                            return ReplyDTO.fastRepseRe(sessionId, queryId, answer, "[]", AIResultTypeEnum.FAQ.getCode(), repseTime);
                        }
                    }
                }
            }

            //如果助手配置了强关联知识库,且知识库没有召回内容，而且不是文档上传问答 则直接返回
            if (Objects.nonNull(config.getDependOnKb())
                    && config.getDependOnKb() == 1 &&
                    (Objects.isNull(retrievedData) || !retrievedData.existDocs()) && CollectionUtils.isEmpty(files)) {
                Long repseTime = System.currentTimeMillis() - llmChatRequstTime;
                //保存问题和答案
                String answer = "抱歉未能找到您要的答案";
                String reference = CollectionUtils.isEmpty(filePathDTOS) ? null : JSONObject.toJSONString(filePathDTOS);
                Integer resultType = CollectionUtils.isEmpty(filePathDTOS) ? AIResultTypeEnum.DEPEND_ON_KB.getCode() : AIResultTypeEnum.FILE_UPLOAD.getCode();
                addQuestionAndAnswerRe(null, dialogueId, aiRequest, answer, reference, resultType, repseTime);
                return ReplyDTO.fastRepseRe(sessionId, queryId, answer, JSON.toJSONString(getCurrentFiles(aiRequest.getFileUids(), filePathDTOS)), resultType, repseTime);
            }

            alParams = modelBasedInferenceParamToJsonRe(dialogueId, extendedConfig, filePathDTOS, webRsDocuments, webDocumentList, sqlMetaData);
            String docs = extendedConfig.getNeedRecall() ? alParams.removeFieldAndGetDos() : "[]";

            Integer resultType = AIResultTypeEnum.LLM.getCode();
            String llmOpenChatUrl = nacosConfig.getLlmOpenChatUrl();
            if (!CollectionUtils.isEmpty(filePathDTOS))
                resultType = AIResultTypeEnum.FILE_UPLOAD.getCode();
            else if (!CollectionUtils.isEmpty(tableSelectedDocuments)) {
                resultType = AIResultTypeEnum.LLM_TABLE.getCode();
                llmOpenChatUrl = nacosConfig.getLlmRotateAnswer();
            }
//        return modelBasedInferenceRe(docs, aiRequest, alParams, dialogueId, inputType, sensWordList, config, filePathDTOS, llmOpenChatUrl, resultType, retrieveSqlFuture);
            return modelBasedInferenceRe(docs, aiRequest, alParams, dialogueId, inputType, sensWordList, config, filePathDTOS, llmOpenChatUrl, resultType, sqlMetaData);
        } catch (ApplicationException e) {
            if (ErrCodeEnum.MODEL_NOT_EXIST.getErrCode().equals(e.getErrCode())) {
                addQuestionAndAnswerRe(null, dialogueId, aiRequest, e.getMessage(), "[]", AIResultTypeEnum.SENSITIVE_WORDS.getCode(), 0l);
                return ReplyDTO.fastReplyRe(sessionId, queryId, e.getMessage(), Lists.newArrayList(), AIResultTypeEnum.LLM.getCode());
            } else
                throw e;
        }
    }

    private String questionRewrite(Long dialogueId, String query, Config config) {
        JSONObject configJson = JSON.parseObject(config.getConfigJson());
        Boolean enabledQuestionRewrite = configJson.getBoolean(ENABLED_QUESTION_REWRITE);
        if (Objects.isNull(enabledQuestionRewrite) || !enabledQuestionRewrite)
            return null;
        String planModelName = configJson.getString(PLAN_MODEL_NAME);
        Integer maxRound = configJson.getInteger(MAX_ROUND);
        List<AiHistory> history = getchatHistory(dialogueId, maxRound);
        return doQuestionRewrite(query, planModelName, history);
    }

    private String doQuestionRewrite(String query, String planModelName, List<AiHistory> chatHistory) {
        //问题改写请求参数
        QuestionRewriteReq questionRewriteReq = new QuestionRewriteReq();
        questionRewriteReq.setModelInfo(modelClient.getSimpByModeName(planModelName));
        questionRewriteReq.setQuery(query);
        questionRewriteReq.setChatHistory(chatHistory);

        String params = JSON.toJSONString(questionRewriteReq);
        log.info("请求问题改接口:{},参数:{}", nacosConfig.getLlmQuestionRewrite(), params);
        String rs;
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity httpEntity = new HttpEntity(params, headers);
            rs = restTemplate.postForObject(nacosConfig.getLlmQuestionRewrite(), httpEntity, String.class);
            log.info("问题改写接口响应结果:{}", rs);
            JSONObject jsonObject = JSON.parseObject(rs);
            Integer responseCode = jsonObject.getInteger(CODE);
            if (Objects.equals(responseCode, 200)) {
                JSONObject dataJson = jsonObject.getJSONObject(DATA);
                query = dataJson.getString(QUERY);
            }
        } catch (Exception e) {
            log.error("问题改写接口出现异常" + e.getMessage());
            return query;
        }
        return query;
    }

    private List<FilePathDTO> convertToFilePathDTOS(List<KnowledgeBaseFileDTO> files) {
        if (CollectionUtils.isEmpty(files))
            return null;
        List<FilePathDTO> filePathDTOS = Lists.newArrayList();
        files.forEach(file -> {
            String txtFilePath;
            FilePathDTO filePathDTO = BeanUtil.copyProperties(file, FilePathDTO.class);
            filePathDTO.setPdfPages(PdfUtils.getPdfPages(file.getConvertedFilePath()));
            String filePath = file.getConvertedFilePath();
            String filePrefix = filePath.substring(0, filePath.lastIndexOf("/"));
            String fileName = null;
            String fileType = file.getFileName().substring(file.getFileName().lastIndexOf(".") + 1);
            if (IndexConstant.IMAGE_HTML_TYPE.contains(fileType))
                fileName = file.getFileName();
            else if (IndexConstant.TEXT_TYPE_LIST.contains(fileType)) {
                fileName = file.getFileName();
                filePath = file.getFilePath();
                filePrefix = filePath.substring(0, filePath.lastIndexOf("/"));
            } else
                fileName = filePath.substring(filePath.lastIndexOf("/") + 1);

            txtFilePath = filePrefix + "/parsed/" + fileName + TXT;
            filePathDTO.setTxtFilePath(txtFilePath);
            filePathDTO.setName(file.getFileName());
            filePathDTO.setSize(file.getFileSize() + "MB");
            filePathDTOS.add(filePathDTO);
        });
        return filePathDTOS;
    }

    private List<AiHistory> getchatHistory(Long dialogueId, Integer maxRound) {
        if (Objects.isNull(maxRound) || maxRound < 0 || maxRound > 32) {
            maxRound = 5;
        }
        List<History> historyList = questionDomainService.getHistoryListByDialogueId(dialogueId, null, "gmtCreate", maxRound);
        List<AiHistory> historyMapList = Lists.newArrayList();
        for (History item : historyList) {
            AiHistory userHistory = new AiHistory();
            userHistory.setQuery(item.getQueryContent());
            userHistory.setAnswer(item.getAnswerContent());
            historyMapList.add(userHistory);
        }
        return historyMapList;
    }
    private List<FilePathDTO> cacheFiles(List<FilePathDTO> files) {
        if (CollectionUtils.isEmpty(files))
            return null;

        files.forEach(file -> {
            String txtFilePath = file.getTxtFilePath();
            if (StringUtils.isEmpty(redissonUtils.get(txtFilePath))) {
                redissonUtils.set(txtFilePath, ReadRemoteFileUtils.readTxt(txtFilePath), FILE_EXPIRE_TIME, TimeUnit.SECONDS);
            }
        });
        return files;
    }

    private String faqSelect(Long dialogueId, AiRequest aiRequest, List<Faq> faqs, ExtendedConfig extendedConfig) {
        List<AiHistory> historyMapList = getchatHistory(dialogueId, extendedConfig.getMaxRound());
        String query = aiRequest.getContent();
        JSONObject faqSelectParam = new JSONObject();
        faqSelectParam.put(MODEL_INFO, modelClient.getSimpByModeName(extendedConfig.getModelName()));
        faqSelectParam.put(TOP_K, Integer.parseInt(extendedConfig.getTopK()));
        faqSelectParam.put(QUERY, query);
        faqSelectParam.put(CHAT_HISTORY, historyMapList);

        List<JSONObject> documents = new ArrayList<>();
        faqs.forEach(faq -> {
            JSONObject doc = new JSONObject();
            doc.put(PAGE_CONTENT, faq.getQuestion() + "@@" + faq.getAnswer());
            doc.put(RERANK_SCORE, Double.parseDouble(faq.getScore()));
            JSONObject metadata = new JSONObject();
            metadata.put(QUESTION, faq.getQuestion());
            metadata.put(ANSWER, faq.getAnswer());
            doc.put(METADATA, metadata);
            documents.add(doc);
        });
        faqSelectParam.put(DOCUMENTS, documents);

        try {
            log.info("faq筛选请求参数:{}", JSON.toJSONString(faqSelectParam));
            HttpEntity httpEntity = new HttpEntity(faqSelectParam);
            String rs = restTemplate.postForObject(nacosConfig.getFaqSelectUrl(), httpEntity, String.class);
            log.info("faq筛选响应结果:{}", rs);
            JSONObject respJson = JSON.parseObject(rs);
            if (!Objects.equals(respJson.getInteger(CODE), 200)) {
                log.error("faq筛选接口调用失败,{}", JSON.toJSONString(respJson));
                throw new ApplicationException(ErrCodeEnum.FAQ_SELECT_ERROR.getErrCode());
            }
            FaqSelectInfo faqSelect = new FaqSelectInfo(respJson);
            return faqSelect.getAnswer();
        } catch (Exception e) {
            log.error("faq筛选出现异常,queryId：" + aiRequest.getQueryId() + ",-knowledge-" + e.getMessage());
            return null;
        }

    }


    private Flux<ReplyDTO> publicQuestionForSingleDocument(AiRequestForSingleDocument aiRequest, InputType inputType) {
        String sessionId = aiRequest.getSessionId();
        String queryId = aiRequest.getQueryId();
        Config config = buildNewConfig(aiRequest);
        // 检索召回+推理（解决流式问题）
        ExtendedConfig extendedConfig = new ExtendedConfig();
        List<SensitiveWordsDTO> sensWordList = Lists.newArrayList();
        ExtendedConfig alParams;
        if (Objects.nonNull(config)) {
            //组装请求参数
            extendedConfig.init(config.getConfigJson());
            //获取敏感词
            sensWordList = getSensitiveWordsByIds(config.getSensitiveWordIds());
            //对问题进行分词，如果有敏感词，则直接返回通用回答
            if (matchSensWord(sensWordList, aiRequest.getContent()).isPresent()) {
                String answer = config.getDefaultAnswer();
                //如果问题命中敏感词，则返回配置的默认回复
                return ReplyDTO.fastReplyRe(sessionId, queryId, answer, null);
            }
            extendedConfig.setQuery(aiRequest.getContent());
        }

        alParams = buildInferenceParamForSingleDocument(extendedConfig, aiRequest.getQaHistory());
        //2.大模型推理服务
        return modelBasedInferenceReForSingleDocument(aiRequest, alParams, inputType, sensWordList, config);
    }

    private Config buildNewConfig(AiRequestForSingleDocument aiRequest) {
        Long newConfigId = aiRequest.getNewConfigId();
        Config config = searchConfigDomainService.getConfigById(newConfigId);
        if (Objects.isNull(config)) {
            //个人的默认助手配置
            config = searchConfigDomainService.getDefaultConfig();
            //系统默认助手配置
            if (Objects.isNull(config)) {
                String defaultConf = nacosConfig.getDefaultSearchConf();
                config = new Config();
                config.setConfigJson(defaultConf);
            }
        }
        //查询模型配置、设置推理思考参数
        buildConfig(config, aiRequest.getEnableThinking(), false);
        String configStr = config.getConfigJson();
        String fileUrl = aiRequest.getFileUrl();
        String kbName = StrUtil.subBetweenAll(fileUrl, "/", "/")[0];
        JSONObject configJson = JSONObject.parseObject(configStr);
        configJson.put(KNOWLEDGE_BASE_NAME, kbName);
        configJson.put(KNOWLEDGE_BASE_NAME_SOURCE, kbName);
        //查询文本块中的数据,并将数据缓存到redis
        configJson.put(FILE_PATHS, Arrays.asList(getSingleDocContent(kbName, fileUrl)));
        config.setConfigJson(JSONObject.toJSONString(configJson));
        return config;
    }

    private String getSingleDocContent(String kbName, String fileUrl) {
        String fileKey = storageProperties.getDefaultStorageProperties().getEndPoint() + "/" + fileUrl;
        if (StringUtils.isEmpty((redissonUtils.get(fileKey)))) {
            String fileName = fileUrl.substring(fileUrl.lastIndexOf("/") + 1);
            Integer pageNo = 1;
            Integer pageSize = 50;
            List<FileChunkDTO> fileChunks = kbClient.getKbFileChunks(kbName, fileName, pageNo, pageSize);
            if (CollectionUtils.isEmpty(fileChunks))
                return fileKey;
            StringBuffer fileContent = new StringBuffer();
            while (true) {
                fileChunks.forEach(item -> fileContent.append(item.getContent() + "\n"));
                if (fileChunks.size() < pageSize)
                    break;
                pageNo++;
                fileChunks = kbClient.getKbFileChunks(kbName, fileName, pageNo, pageSize);
            }
            redissonUtils.set(fileKey, fileContent, FILE_EXPIRE_TIME, TimeUnit.SECONDS);
        }
        return fileKey;
    }

    private Flux<ReplyDTO> publicQuestion(AiRequest aiRequest, InputType inputType) {
        llmChatRequstTime = System.currentTimeMillis();
        Long dialogueId = saveOrUpdateDialogue(aiRequest);//2694L;//2804L;// 2816L;//
        List<Map<String, Object>> documents = new ArrayList<>();
        List<Map<String, Object>> webRsDocuments = new ArrayList<>();
        JSONObject alParams;
        String indexRecallJson = "[]";
        String sessionId = aiRequest.getSessionId();
        String queryId = aiRequest.getQueryId();

        Dialogue dialogue = dialogueDomainService.getDialogueById(dialogueId);
        Config config = dialogue.getConfig();
        // R13-SEC-A1（问答主链 /question）：配置指向的知识库必须在本主体授权范围内
        assertKnowledgeBaseReadable(config);

        // 检索召回+推理（解决流式问题）
        // 判断是否配置默认配置文件
        JSONObject jsonConfig;
        List<SensitiveWordsDTO> sensWordList = Lists.newArrayList();
        //组装请求参数
        jsonConfig = JSON.parseObject(config.getConfigJson());
        //获取敏感词
        sensWordList = getSensitiveWordsByIds(config.getSensitiveWordIds());
        log.info("sensitive words are {}", JSON.toJSONString(sensWordList));
        //对问题进行分词，如果有敏感词，则直接返回通用回答
        if (matchSensWord(sensWordList, aiRequest.getContent()).isPresent()) {
            String answer = config.getDefaultAnswer();
            //保存问题和答案
            addQuestionAndAnswer(null, dialogueId, aiRequest, answer, null);
            //如果问题命中敏感词，则返回配置的默认回复
            return ReplyDTO.fastReply(sessionId, queryId, answer, null);
        }

        jsonConfig.put(QUERY, aiRequest.getContent());

        if (StringUtils.isNotBlank(jsonConfig.getString(KNOWLEDGE_BASE_NAME))) {
            //检索召回组装json数据
            alParams = retrieveRecallParamToJson(jsonConfig);

            //1.调用检索召回接口（）
            indexRecallJson = retrieveRecall(aiRequest, alParams, dialogueId, Boolean.FALSE);
            if (Objects.nonNull(indexRecallJson)) {
                List<Map> itemList = JSON.parseArray(indexRecallJson, Map.class);
                for (Map item : itemList) {
                    String pageContent = String.valueOf(item.get(PAGE_CONTENT));
                    String orderNum = String.valueOf(item.get(ORDER_NUM));
                    Map<String, Object> itemMap = new HashMap<>();
                    itemMap.put(PAGE_CONTENT, pageContent);
                    itemMap.put(ORDER_NUM, orderNum);
                    documents.add(itemMap);

                    Map<String, Object> webRsMap = new HashMap<>();
                    JSONObject metadata = (JSONObject) item.get(METADATA);
                    String type = String.valueOf(item.get(TYPE));
                    String score = String.valueOf(item.get(SCORE));
                    webRsMap.put(PAGE_CONTENT, pageContent);
                    webRsMap.put(ORDER_NUM, orderNum);
                    webRsMap.put(PARSED_FILE_PATH, getParsedFilePath(metadata));
                    String source = metadata.getString(SOURCE);
                    metadata.put(SOURCE, storageProperties.getDefaultStorageProperties().getEndPoint() + "/" + source);
                    webRsMap.put(METADATA, metadata);
                    webRsMap.put(TYPE, type);
                    webRsMap.put(SCORE, score);
                    webRsDocuments.add(webRsMap);
                }

                if (itemList.size() > 0) {
                    Map oneItem = itemList.get(0);
                    if (Objects.nonNull(oneItem) && Objects.nonNull(oneItem.get(FAQ_ANSWER))) {
                        String answer = oneItem.get(FAQ_ANSWER).toString();
                        if (matchSensWord(sensWordList, answer).isPresent()) {
                            answer = config.getDefaultAnswer();
                            webRsDocuments = null;
                        }
                        addQuestionAndAnswer(alParams, dialogueId, aiRequest, answer, webRsDocuments);
                        return ReplyDTO.fastReply(sessionId, queryId, answer, webRsDocuments);
                    }
                }
            }
        }
        //如果助手配置了强关联知识库,且知识库没有召回内容，则直接返回
        if ((Objects.nonNull(config.getDependOnKb()) && config.getDependOnKb() == 1)
                && (Objects.isNull(indexRecallJson) || StringUtils.equals(indexRecallJson, "[]"))) {
            //保存问题和答案
            Long respTime = System.currentTimeMillis() - llmChatRequstTime;
            String answer = "抱歉未能找到您要的答案";
            addQuestionAndAnswerRe(null, dialogueId, aiRequest, answer, null, AIResultTypeEnum.DEPEND_ON_KB.getCode(), respTime);
            return ReplyDTO.fastReplyRe(sessionId, queryId, answer, null, AIResultTypeEnum.DEPEND_ON_KB.getCode(), respTime);
        }

        alParams = modelBasedInferenceParamToJson(dialogueId, jsonConfig);
        alParams.put(DOCUMENTS, documents);

        //2.大模型推理服务
        return modelBasedInference(webRsDocuments, aiRequest, alParams, dialogueId, inputType, sensWordList, config);
    }

    private void addQuestionAndAnswer(JSONObject alParams, Long dialogueId, AiRequest aiRequest, String answer, List<Map<String, Object>> reference) {
        //FIXME 这里建议换成mapstruct 有更好的性能
        Question question = new Question();
        if (Objects.nonNull(alParams)) {
            question = BeanUtil.copyProperties(alParams, Question.class);
            question.buildQuestion(alParams.getString(MODEL_NAME), dialogueId, aiRequest, alParams.toJSONString());
        } else {
            question.buildQuestion(null, dialogueId, aiRequest, null);
        }
        Long questionId = questionDomainService.addOrUpdateQuestionByDialogueIdAndFrontUuid(question);
        Answer answerObj = new Answer();
        answerObj.setType(aiRequest.getType());
        answerObj.setDialogueId(dialogueId);
        answerObj.setQuestionId(questionId);
        answerObj.setContent(answer);
        if (Objects.nonNull(reference)) {
            answerObj.setReference(JSON.toJSONString(reference));
        }
        answerDomainService.addOrUpdateAnswerByDialogueIdAndQuestionId(answerObj);
    }

    private void addQuestionAndAnswerRe(ExtendedConfig alParams, Long dialogueId, AiRequest aiRequest, String answer, String reference, Integer resultType, Long respTime) {
        Question question = new Question();
        if (Objects.nonNull(alParams)) {
            question = BeanUtil.copyProperties(alParams, Question.class);
            question.buildQuestion(alParams.getModelName(), dialogueId, aiRequest, alParams.getConfigJSONString());
        } else {
            question.buildQuestion(null, dialogueId, aiRequest, null);
        }
        Long questionId = questionDomainService.addOrUpdateQuestionByDialogueIdAndFrontUuid(question);
        Answer answerObj = new Answer();
        answerObj.setRespTime(respTime);
        answerObj.setType(aiRequest.getType());
        answerObj.setDialogueId(dialogueId);
        answerObj.setQuestionId(questionId);
        answerObj.setContent(StringUtils.isNotBlank(answer) ? answer : "");
        answerObj.setRetrieveRecallParam(aiRequest.getConfig());
        answerObj.setResultType(resultType);
        answerObj.setReference(reference);
        answerDomainService.addOrUpdateAnswerByDialogueIdAndQuestionId(answerObj);
    }

    /**
     * 返回命中的敏感词
     *
     * @param sensWordList
     * @param content
     * @return
     */
    private Optional<SensitiveWordsDTO> matchSensWord(List<SensitiveWordsDTO> sensWordList, String content) {
        //1.判断问题中是否存在敏感词
        return Optional.ofNullable(sensWordList).map(senseWords ->
                senseWords.stream().filter(word -> containsSensWord(word.getWords(), content)).findAny().orElse(null)
        );
    }

    @Trace
    private List<SensitiveWordsDTO> getSensitiveWordsByIds(String sensitiveWordIds) {
        //1.根据敏感词id字符串解析出Long[]
        Long[] ids = Optional.ofNullable(sensitiveWordIds)
                .map(str -> str.split(","))
                .map(array -> Arrays.stream(array).filter(StringUtils::isNotBlank).map(Long::valueOf).toArray(Long[]::new))
                .orElse(new Long[0]);

        //2.根据敏感词id查敏感词库
        if (ids.length == 0) {
            return Lists.newArrayList();
        }
        return sensitiveWordsClient.getListByIds(ids);
    }

    /**
     * 判断问题中是否包含敏感词
     *
     * @param words
     * @param content
     * @return
     */
    @Trace
    private boolean containsSensWord(LinkedHashSet<String> words, String content) {
//        //0.对词语进行trim操作
//        words = words.stream().map(str -> str.trim()).collect(Collectors.toCollection(LinkedHashSet<String>::new));
//        //1.对问题进行分词
//        HashSet<String> questionSet = AnsjUtils.nlpAnalysisParse(content);
//        log.info("splited question:{}", JSON.toJSONString(questionSet));
//        //2.取交集
//        questionSet.retainAll(words);
//        //3.判断交集是否为空
//        return !CollectionUtils.isEmpty(questionSet);


        //动态添加用户自定义词典
        return ansjParseWordUtils.checkHitSensitiveWords(content, words);
    }


    private String publicQuestionForCZBank(AiCZBankRequest aiRequest, InputType inputType) {
        List<Map> documents = new ArrayList<>();
        JSONObject alParams;
        String indexRecallJson = "[]";

        Config config = searchConfigDomainService.getConfigById(aiRequest.getConfigId());
        if (Objects.isNull(config)) {
            config = searchConfigDomainService.getDefaultConfig();
        }

        JSONObject jsonConfig;

        if (Objects.nonNull(config)) {
            //组装请求参数
            jsonConfig = JSON.parseObject(config.getConfigJson());
            jsonConfig.put(QUERY, aiRequest.getContent());

            if (StringUtils.isNotBlank(jsonConfig.getString(KNOWLEDGE_BASE_NAME))) {
                //检索召回组装json数据
                alParams = retrieveRecallParamToJson(jsonConfig);

                //1.调用检索召回接口（）
                indexRecallJson = retrieveRecallForCZBank(aiRequest, alParams);
                System.out.println(indexRecallJson);
                if (Objects.nonNull(indexRecallJson)) {
                    List<Map> itemList = JSON.parseArray(indexRecallJson, Map.class);
                    if (itemList.size() > 0) {
                        Map oneItem = itemList.get(0);
                        if (Objects.nonNull(oneItem) && Objects.nonNull(oneItem.get(FAQ_ANSWER))) {
                            return oneItem.get(FAQ_ANSWER).toString();
                        }
                    }
                    for (Map item : itemList) {
                        String pageContent = String.valueOf(item.get(PAGE_CONTENT));
                        String orderNum = String.valueOf(item.get(ORDER_NUM));
                        Map<String, String> itemMap = new HashMap<>();
                        itemMap.put(PAGE_CONTENT, pageContent);
                        itemMap.put(ORDER_NUM, orderNum);
                        documents.add(itemMap);
                    }
                }
            }
        } else {
            jsonConfig = JSON.parseObject(nacosConfig.getDefaultSearchConf());
            jsonConfig.put(QUERY, aiRequest.getContent());
        }

        alParams = modelBasedInferenceParamToJsonForCZBank(jsonConfig);
        alParams.put(DOCUMENTS, documents);

        //2.大模型推理服务
        return modelBasedInferenceForCZBank(indexRecallJson, aiRequest, alParams, inputType);
    }

    private Long saveOrUpdateDialogue(AiRequest aiRequest) {
        String apiKey = UserContext.getUser().getApiKey();
        Dialogue reqDialogue = DialogueConvertor.INSTANCE.aiRequest2Dialogue(aiRequest);
        //获取configId
        Long configId = reqDialogue.getConfigId();
        Config config;
        Boolean permission = false;
        //获取旧的对话
        Dialogue dbDialogue = dialogueDomainService.getDialogueBySessionId(aiRequest.getSessionId());
        if (StringUtils.isNotEmpty(apiKey)) {
            if (!apiKeyInfoDomainService.checkApiKey(apiKey)) {
                //apikey方式调用，需要校验apiKye的合法性
                log.error("apiKey:【{}】不合法", apiKey);
                throw new ApplicationException(ErrCodeEnum.ID_IS_NULL_ERROR);
            }
            String desEncrypt = aesEncryptUtil.desEncrypt(apiKey.replace(QaConstant.API_KEY_PREFIX, ""));
            JSONObject apiKeyJson = JSON.parseObject(desEncrypt);

            assert apiKeyJson != null;
            configId = apiKeyJson.getLong(QaConstant.BIZ_TARGET_ID);
            config = searchConfigDomainService.getConfigById(configId);
            reqDialogue.setConfig(config);
            reqDialogue.setConfigId(configId);
            permission = true;
        } else if (StringUtils.isEmpty(apiKey) && Objects.nonNull(configId) && configId > 0) {
            //获取config
            config = searchConfigDomainService.getConfigById(configId);
            //自己创建的检索配置有权限
            permission = Objects.nonNull(config) && config.getCreateBy().equals(UserContext.getUser().getUserName());
            //判断是否有数据权限
            if (!permission && Objects.nonNull(config)) {
                permission = authClient.isPermission(PrivilegeTypeEnums.INDEX_CONF.getCode(), configId);
            }
            if (permission) {
                reqDialogue.setConfig(config);
                reqDialogue.setConfigId(configId);
                if (Objects.nonNull(dbDialogue) && StringUtils.isNotBlank(dbDialogue.getConfigHistory()) && !configId.equals(dbDialogue.getConfigId())) {
                    JSONArray configHistorys = JSON.parseArray(dbDialogue.getConfigHistory());
                    configHistorys.add(config);
                    reqDialogue.setConfigHistory(JSON.toJSONString(configHistorys));
                } else
                    reqDialogue.setConfigHistory(JSON.toJSONString(Arrays.asList(config)));
            }
        }

        //没有助手配置的权限 || 没有指定组手配置
        if (!permission || Objects.isNull(configId)) {
            //个人的默认助手配置
            config = searchConfigDomainService.getDefaultConfig();
            //系统默认助手配置
            if (Objects.isNull(config)) {
                String defaultConf = nacosConfig.getDefaultSearchConf();
                config = new Config();
                config.setConfigJson(defaultConf);
            }
            reqDialogue.setConfig(config);
            reqDialogue.setConfigId(configId);
        }

        // R13-SEC-A1（问答侧）：助手配置本身有权限，不代表配置指向的知识库可用；
        // 这里对配置里的 knowledge_base_name 再做一次对象级授权，避免"能问 = 能读任意库"。
        assertKnowledgeBaseReadable(reqDialogue.getConfig());
        return dialogueDomainService.addOrUpdateBySessionId(reqDialogue);
    }

    /**
     * 校验当前主体对配置指向的知识库至少具备读权限。
     * 取不到知识库名（例如直连数据库问答的配置）时不做拦截；取到但无权限一律拒绝。
     */
    private void assertKnowledgeBaseReadable(Config config) {
        if (config == null || StringUtils.isBlank(config.getConfigJson())) {
            return;
        }
        String kbName;
        try {
            kbName = JSONObject.parse(config.getConfigJson()).getString("knowledge_base_name");
        } catch (Exception ex) {
            log.warn("parse config json failed when checking kb permission: {}", ex.getMessage());
            return;
        }
        if (StringUtils.isBlank(kbName)) {
            return;
        }
        Integer permission;
        try {
            permission = kbClient.myPermissionByPrimitive(kbName);
        } catch (Exception ex) {
            log.error("query kb permission failed for {}: {}", kbName, ex.getMessage());
            throw new ApplicationException(ErrCodeEnum.INSUFFICIENT_PERMISSIONS);
        }
        if (permission == null || permission < 1) {
            log.warn("R13-SEC-A1 deny qa: kb={} permission={}", kbName, permission);
            throw new ApplicationException(ErrCodeEnum.INSUFFICIENT_PERMISSIONS);
        }
    }

    private void buildConfig(Config config, Boolean enableThinking, Boolean enableWebsearch) {
        String configInfo = config.getConfigJson();
        JSONObject confJson = JSONObject.parseObject(configInfo);
        confJson.put(ENABLE_THINKING, enableThinking);
        confJson.put(ENABLE_WEB_SEARCH, enableWebsearch);
        String modelName = confJson.getString(MODEL_NAME);
        String rerankModelName = confJson.getString(RERANK_MODEL_NAME);
        //推理模型信息
        confJson.put(MODEL_INFO, modelClient.getSimpByModeName(modelName));
        //rerank模型(召回和推理接口使用)
        confJson.put(RERANK_MODEL_INFO, StringUtils.isNotBlank(rerankModelName) ? modelClient.getSimpByModeName(rerankModelName) : null);
        config.setConfigJson(JSONObject.toJSONString(confJson));
    }

    /**
     * 2.调用大模型推理服务（检索召回内容作为推理服务的入参）
     *
     * @param docs
     * @param aiRequest
     * @param alParams
     * @param dialogueId
     * @return
     */
    @Trace
    private Flux<ReplyDTO> modelBasedInference(List<Map<String, Object>> docs, AiRequest aiRequest, JSONObject alParams, Long dialogueId, InputType inputType, List<SensitiveWordsDTO> sensWordList, Config config) {
        log.info("modelBasedInference--模型推理请求参数:" + alParams);
        Question question = BeanUtil.copyProperties(alParams, Question.class);
        question.setAlgModel(String.valueOf(alParams.get(MODEL_NAME)));
        question.setContent(aiRequest.getContent());
        question.setType(aiRequest.getType());
        question.setFrontUuid(aiRequest.getQueryId());
        question.setDialogueId(dialogueId);
        question.setAudioUrl(aiRequest.getAudioUrl());
        question.setAlgParams(alParams.toJSONString());

        Long questionId = questionDomainService.addOrUpdateQuestionByDialogueIdAndFrontUuid(question);
        String sessionId = aiRequest.getSessionId();
        String queryId = aiRequest.getQueryId();
        StringBuffer contentStrBuffer = new StringBuffer();


        String webRsDocuments = JSON.toJSONString(docs);

        Answer answerObj = new Answer();
        answerObj.setType(aiRequest.getType());
        answerObj.setDialogueId(dialogueId);
        answerObj.setQuestionId(questionId);
        answerObj.setResultType(AIResultTypeEnum.LLM.getCode());
        AtomicReference<Boolean> isErrFlag = new AtomicReference<>(null);
        aiRequest.setDialogueId(dialogueId);
        Flux<ReplyDTO> thirdPartyStream = webLlmOpenChatClient.post()
                .uri(nacosConfig.getLlmOpenChatUrl())
                .contentType(MediaType.APPLICATION_JSON)
                .body(BodyInserters.fromValue(alParams)) //参数
                .accept(MediaType.TEXT_EVENT_STREAM) //接收text/event-stream流的数据
                .retrieve()
                .bodyToFlux(String.class) //输出格式
                .map(s -> doRunRs(s, contentStrBuffer, answerObj, aiRequest, isErrFlag, inputType, sensWordList, webRsDocuments, null, null))
                .onErrorResume(Exception.class, ex -> doErrorResume(aiRequest, ex, contentStrBuffer, isErrFlag, config)) //请求失败
                .doFinally(signalType -> doFinally(isErrFlag, aiRequest, dialogueId, contentStrBuffer, answerObj)); //请求完成后
        return sendHeartBeat(sessionId, queryId, null).concatWith(thirdPartyStream);
    }

    //    private Flux<ReplyDTO> modelBasedInferenceRe(String docs, AiRequest aiRequest, ExtendedConfig alParams, Long dialogueId, InputType inputType, List<SensitiveWordsDTO> sensWordList, Config config, List<FilePathDTO> filePathDTOS, String modelUrl, Integer resultType, CompletableFuture<RetrieveSqlDataReference> retrieveSqlFuture) {
    private Flux<ReplyDTO> modelBasedInferenceRe(String docs, AiRequest aiRequest, ExtendedConfig alParams, Long dialogueId, InputType inputType, List<SensitiveWordsDTO> sensWordList, Config config, List<FilePathDTO> filePathDTOS, String modelUrl, Integer resultType, SqlMetaData sqlMetaData) {
        //异步去读sql data json file
        log.info("modelBasedInference-- url:{},模型推理请求参数:{}", modelUrl, alParams.getConfigJSONString());
        Question question = QuestionConvertor.INSTANCE.extendedConfig2Question(alParams);
        question.setAlgModel(alParams.getModelName());
        question.setContent(aiRequest.getContent());
        question.setType(aiRequest.getType());
        question.setFrontUuid(aiRequest.getQueryId());
        question.setDialogueId(dialogueId);
        question.setAudioUrl(aiRequest.getAudioUrl());
        alParams.setCurrentFiles(getCurrentFiles(aiRequest.getFileUids(), filePathDTOS));
        question.setAlgParams(alParams.getConfigJSONString());

        Long questionId = questionDomainService.addOrUpdateQuestionByDialogueIdAndFrontUuid(question);
        String sessionId = aiRequest.getSessionId();
        String queryId = aiRequest.getQueryId();
        StringBuffer contentStrBuffer = new StringBuffer();

        Answer answerObj = new Answer();
        answerObj.setType(aiRequest.getType());
        answerObj.setDialogueId(dialogueId);
        answerObj.setQuestionId(questionId);
        answerObj.setResultType(resultType);

        aiRequest.setDialogueId(dialogueId);

        AtomicReference<Boolean> isErrFlag = new AtomicReference<>(null);
        Flux<ReplyDTO> thirdPartyStream = webLlmOpenChatClient.post()
                .uri(modelUrl)
                .contentType(MediaType.APPLICATION_JSON)
                .body(BodyInserters.fromValue(alParams.getConfigJSONString())) //参数
                .accept(MediaType.TEXT_EVENT_STREAM) //接收text/event-stream流的数据
                .retrieve()
                .bodyToFlux(String.class) //输出格式
                .map(s -> doRunRs(s, contentStrBuffer, answerObj, aiRequest, isErrFlag, inputType, sensWordList, docs, filePathDTOS, sqlMetaData))
                .onErrorResume(Exception.class, ex -> doErrorResume(aiRequest, ex, contentStrBuffer, isErrFlag, config)) //请求失败
                .doFinally(signalType -> doFinally(isErrFlag, aiRequest, dialogueId, contentStrBuffer, answerObj)); //请求完成后
        return sendHeartBeat(sessionId, queryId, filePathDTOS).concatWith(thirdPartyStream);
    }

    private String getUserFeature() {
        try {
            return Optional.ofNullable(authClient.getUserInfo()).map(UserInfoDTO::getFeature).orElse("");
        } catch (Exception e) {
            return "";
        }
    }

    private Flux<ReplyDTO> modelBasedInferenceReForSingleDocument(AiRequestForSingleDocument aiRequest, ExtendedConfig alParams, InputType inputType, List<SensitiveWordsDTO> sensWordList, Config config) {
        log.info("modelBasedInference--模型推理请求参数:" + alParams.getConfig());
        String sessionId = aiRequest.getSessionId();
        String queryId = aiRequest.getQueryId();
        StringBuffer contentStrBuffer = new StringBuffer();
        Answer answerObj = new Answer();
        answerObj.setType(aiRequest.getType());
        AtomicReference<Boolean> isErrFlag = new AtomicReference<>(null);
        Flux<ReplyDTO> thirdPartyStream = webLlmOpenChatClient.post()
                .uri(nacosConfig.getLlmOpenChatUrl())
                .contentType(MediaType.APPLICATION_JSON)
                .body(BodyInserters.fromValue(alParams.getConfigJSONString())) //参数
                .accept(MediaType.TEXT_EVENT_STREAM) //接收text/event-stream流的数据
                .retrieve()
                .bodyToFlux(String.class) //输出格式
                .map(s -> doRunRsForSingleDocument(s, contentStrBuffer, answerObj, aiRequest, isErrFlag, inputType, sensWordList))
                .onErrorResume(Exception.class, ex -> doErrorResumeForSingleDocument(aiRequest, ex, contentStrBuffer, isErrFlag, config)); //请求失败
//                .doFinally(signalType -> doFinally(isErrFlag, aiRequest, dialogueId, contentStrBuffer, answerObj)); //请求完成后
        return sendHeartBeat(sessionId, queryId, null).concatWith(thirdPartyStream);
    }

    private Flux<ReplyDTO> sendHeartBeat(String sessionId, String queryId, List<FilePathDTO> filePathDTOS) {
        ReplyDTO firstReplyDTO = new ReplyDTO();
        firstReplyDTO.setSessionId(sessionId);
        firstReplyDTO.setQueryId(queryId);
        firstReplyDTO.setLastDate(new Date());
        firstReplyDTO.setStatus(ReplyStatusEnums.RUN);
        firstReplyDTO.setReference(null);
        ReplyContentDTO firstReplyContentDTO = new ReplyContentDTO();
        firstReplyContentDTO.setContent("");
        firstReplyContentDTO.setType(MARKDOWN);
        firstReplyDTO.setReply(firstReplyContentDTO);
        firstReplyDTO.setFilePaths(CollectionUtils.isEmpty(filePathDTOS) ? null : JSON.toJSONString(filePathDTOS));
        return Flux.just(firstReplyDTO).delayElements(Duration.ofSeconds(0));
    }

    private String modelBasedInferenceForCZBank(String docs, AiCZBankRequest aiRequest, JSONObject alParams, InputType inputType) {
        log.info("modelBasedInference--模型推理请求参数:" + alParams);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<String> requestEntity = new HttpEntity<>(JSON.toJSONString(alParams), headers);
        RestTemplate restTemplate = new RestTemplate();
        ResponseEntity<String> responseEntity = restTemplate.exchange(nacosConfig.getLlmOpenChatUrl(), HttpMethod.POST, requestEntity, String.class);
        String body = responseEntity.getBody();
        log.info("大模型回复结果:{}", body);
        JSONObject jsonObject = JSON.parseObject(body);
        return jsonObject.getString(ANSWER);
    }

    @Trace
    private ReplyDTO doRunRs(String s, StringBuffer contentStrBuffer, Answer answerObj, AiRequest aiRequest, AtomicReference<Boolean> isErrFlag, InputType inputType, List<SensitiveWordsDTO> sensWordList, String retrieveDocs, List<FilePathDTO> filePathDTOS, SqlMetaData sqlMetaData) {
        log.info("queryId：" + aiRequest.getQueryId() + ",content：" + s);
        ReplyDTO replyDTO = new ReplyDTO();
        replyDTO.setSessionId(aiRequest.getSessionId());
        replyDTO.setQueryId(aiRequest.getQueryId());
        replyDTO.setLastDate(new Date());
        replyDTO.setResultType(answerObj.getResultType());
        ReplyContentDTO replyContentDTO = new ReplyContentDTO();
        replyContentDTO.setType(MARKDOWN);
        try {
            String answer = "";
            String end = null;
            String docs = null;
            if (StringUtils.isNotEmpty(s)) {
                JSONObject jsonObject = JSON.parseObject(s);
                //获取JSON对象中的值
                answer = jsonObject.getString(ANSWER);
                if (StringUtils.isNotEmpty(jsonObject.getString(PROMPT_CONTENT)))
                    promptContent = jsonObject.getString(PROMPT_CONTENT);
                if (matchSensWord(sensWordList, answer).isPresent()) {
                    log.info("answer:{} contains sensitiveWords", answer);
                    answerObj.setReference(null);
                    throw new ApplicationException(ErrCodeEnum.CONTAINS_SENS_WORD);
                }
                end = jsonObject.getString(END);
                docs = jsonObject.getString(DOCS);
            }
            if (answer != null) {
                replyDTO.setStatus(ReplyStatusEnums.RUN);
                contentStrBuffer.append(answer);
                if (inputType.equals(InputType.MONTAGE)) {
                    replyContentDTO.setContent(contentStrBuffer.toString());
                } else {
                    //返回
                    replyContentDTO.setContent(answer);
                }
                replyDTO.setReply(replyContentDTO);
            } else {
                if (inputType.equals(InputType.MONTAGE)) {
                    replyContentDTO.setContent(contentStrBuffer.toString());
                } else {
                    replyContentDTO.setContent("");
                }
                if (end != null) {
                    replyDTO.setStatus(ReplyStatusEnums.PARSE_SUCCESS);
                    answerObj.setReference(CollectionUtils.isEmpty(filePathDTOS) ? retrieveDocs : JSONObject.toJSONString(filePathDTOS));
                    if (isErrFlag.get() == null) {
                        isErrFlag.set(false);
                    }


                    answerObj.setContent(contentStrBuffer.toString());
                    //等待线程执行完成
                    if (Objects.nonNull(sqlMetaData)) {
                        try {
                            RetrieveSqlDataReference dataReference = sqlMetaData.getRetrieveSqlDataReference();
                            log.info("retrieveSqlFuture:{}", dataReference);
                            String retrieveTag = addRetrieveSqlDataTag(replyContentDTO, dataReference);
                            addDatabaseReference(replyDTO, dataReference);
                            answerObj.setDatabaseReference(dataReference.getReference());
                            contentStrBuffer.append(retrieveTag);
                            answerObj.setContent(contentStrBuffer.toString());
                        } catch (Exception e) {
                            log.error("retrieveSqlFuture append to answer error", e);
                        }
                    }
                    //溯源标签id过滤召回文本块(filePathDTOS不为空是文档上传问答,不需要处理)
                    if (CollectionUtils.isEmpty(filePathDTOS))
                        answerObj.setReference(filterDocs(answerObj.getContent(), answerObj.getReference()));
                    replyDTO.setReference(answerObj.getReference());
                    //replyDTO.setLlmType(llmType);
                    replyDTO.setResultType(answerObj.getResultType());
                    replyDTO.setTokens(contentStrBuffer.length());
                    if (!Objects.isNull(llmChatRequstTime)) {
                        Long respTime = System.currentTimeMillis() - llmChatRequstTime;
                        replyDTO.setRespTime(respTime);
                        answerObj.setRespTime(respTime);
                    }
                    answerObj.setResultType(replyDTO.getResultType());
                    replyDTO.setPromptContent(promptContent);
                    answerDomainService.addOrUpdateAnswerByDialogueIdAndQuestionId(answerObj);
                    log.info("queryId：" + aiRequest.getQueryId() + ",content：结束");
                } else {
                    replyDTO.setStatus(ReplyStatusEnums.RUN);
                    if (docs != null) {
                        replyDTO.setReference(docs);
                        answerObj.setReference(docs);
                        answerDomainService.addOrUpdateAnswerByDialogueIdAndQuestionId(answerObj);
                    }
                }

                replyDTO.setReply(replyContentDTO);
            }
        } catch (ApplicationException e) {
            log.error("ApplicationException:{}", e);
            if (e.getErrCode().equals(ErrCodeEnum.CONTAINS_SENS_WORD.getErrCode())) {
                throw e;
            }
        } catch (Exception e) {
            e.printStackTrace();
            log.error("error:{}", e);
            replyDTO.setStatus(ReplyStatusEnums.PARSE_FAIL);
            if (inputType.equals(InputType.MONTAGE)) {
                replyContentDTO.setContent(contentStrBuffer.toString());
            } else {
                replyContentDTO.setContent("");
            }
            replyContentDTO.setType(MARKDOWN);
            replyDTO.setReply(replyContentDTO);
            isErrFlag.set(true);
            log.error("queryId：" + aiRequest.getQueryId() + ",s：" + s);
            log.error("queryId：" + aiRequest.getQueryId() + ",处理AI异常json：" + e.getLocalizedMessage());
        }
        return replyDTO;
    }

    private String addRetrieveSqlDataTag(ReplyContentDTO replyContentDTO, RetrieveSqlDataReference sqlDataReference) {
        if (Objects.isNull(replyContentDTO)) {
            replyContentDTO = new ReplyContentDTO();
            replyContentDTO.setType(MARKDOWN);
            replyContentDTO.setContent("");
        }
        if (Objects.nonNull(sqlDataReference)) {
            String tag = sqlDataReference.getTag();
            if (StringUtils.isNotBlank(tag)) {
                String newAnswer = replyContentDTO.getContent() + "\n\n" + tag;
                replyContentDTO.setContent(newAnswer);
            }
        }
        return replyContentDTO.getContent();
    }

    private void addDatabaseReference(ReplyDTO replyDTO, RetrieveSqlDataReference sqlDataReference) {
        if (Objects.nonNull(sqlDataReference)) {
            String reference = sqlDataReference.getReference();
            replyDTO.setDatabaseReference(reference);
        }
    }

    private RetrieveSqlDataReference appendSqlDataToAnswer(RetrieveSql result, Long dialogueId) {
        RetrieveSqlDataReference dataReference = new RetrieveSqlDataReference();
        //获取json file的数据
        if (Objects.nonNull(result) && StringUtils.isNoneBlank(result.getSql())) {

            String searchKey = String.format("sql-data:%s", dialogueId);
            if (redissonUtils.exists(searchKey)) {
                log.info("searchKey:{} exists", searchKey);

                dataReference.setFilePath(redissonUtils.get(searchKey));
                if (StringUtils.isNotEmpty(dataReference.getFilePath())) {
                    log.info("sql file filePath:{} exists", dataReference.getFilePath());
                    try {
                        ResponseEntity<JSONPagination.PageResult<JsonNode>> responseEntity = kbClient.pageFileStream(PageFileStreamReq.from(dataReference.getFilePath(), false));
                        JSONPagination.PageResult<JsonNode> body = responseEntity.getBody();
                        if (Objects.nonNull(body)) {
                            dataReference.setTag(getSqlTag(body));
                            String tableName = result.getTableName();
                            Long databaseId = result.getDatabaseId();
                            dataReference.setReference(getSqlData(body, dataReference.getFilePath(), databaseId, tableName));
                        }
                    } catch (IOException | FileStorageException e) {
                        log.error("appendSqlDataToAnswer:", e);
                        throw new RuntimeException(e);
                    }

                }
            }
            return dataReference;
        }

        return null;
    }

    private CompletableFuture<RetrieveSqlDataReference> appendSqlDataToAnswerAysnc
            (LLMClientResp<RetrieveSql> result, JSONObject helperConfig, Long dialogueId) {
        //如果配置了数据库
        if (helperConfig.containsKey(DATABASE_NAME) && !helperConfig.getJSONArray(DATABASE_NAME).isEmpty()) {
            AtomicReference<RetrieveSqlDataReference> sqlDataRef = new AtomicReference<>(new RetrieveSqlDataReference());
            //异步获取json file的数据
            if (Objects.nonNull(result) && Objects.nonNull(result.getData()) && StringUtils.isNoneBlank(result.getData().getSql())) {
                return CompletableFuture.supplyAsync(() -> {
                            String searchKey = String.format("sql-data:%s", dialogueId);
                            if (redissonUtils.exists(searchKey)) {
                                log.info("searchKey:{} exists", searchKey);
                                RetrieveSqlDataReference dataReference = new RetrieveSqlDataReference();
                                dataReference.setFilePath(redissonUtils.get(searchKey));
                                sqlDataRef.set(dataReference);
                                if (StringUtils.isNotEmpty(sqlDataRef.get().getFilePath())) {
                                    log.info("sql file filePath:{} exists", sqlDataRef.get().getFilePath());
                                    try {
                                        ResponseEntity<JSONPagination.PageResult<JsonNode>> responseEntity = kbClient.pageFileStream(PageFileStreamReq.from(sqlDataRef.get().getFilePath(), false));
                                        JSONPagination.PageResult<JsonNode> body = responseEntity.getBody();
                                        if (Objects.nonNull(body)) {
                                            sqlDataRef.get().setTag(getSqlTag(body));
                                            String tableName = result.getData().getTableName();
                                            //TODO dbName让算法端返回
                                            Long databaseId = result.getData().getDatabaseId();
                                            sqlDataRef.get().setReference(getSqlData(body, sqlDataRef.get().getFilePath(), databaseId, tableName));
                                        }
                                    } catch (IOException | FileStorageException e) {
                                        log.error("appendSqlDataToAnswer:", e);
                                        throw new RuntimeException(e);
                                    }

                                }
                            }
                            return sqlDataRef.get();
                        }, asyncExecutor).orTimeout(10, TimeUnit.MINUTES)
                        .handle((composeResult, ex) -> {
                            if (ex != null) {
                                log.info("read json file success!!sqlDataRef:{}", JSON.toJSONString(sqlDataRef.get()));
                            }
                            return composeResult;
                        }).exceptionally(ex -> {
                            log.error("appendSqlDataToAnswer failed...:", ex);
                            throw new RuntimeException("appendSqlDataToAnswer failed...:", ex);
                        });
            }
        }
        return null;
    }

    /**
     * 和前端约定的sqldata标签
     *
     * @param body
     * @return
     */
    private String getSqlTag(JSONPagination.PageResult<JsonNode> body) {
        String id = UUID.randomUUID().toString();
        body.setId(id);
        return String.format(RETRIEVE_SQL_TAG, id);
    }

    private String getSqlData(JSONPagination.PageResult<JsonNode> body, String filePath, Long
            databaseId, String tableName) {
        TLDatabaseDTO db = kbClient.queryDB(databaseId);

        DataReference dataRef = new DataReference();
        dataRef.setId(body.getId());
        DataReference.RetrieveSqlData retrieveSqlData = new DataReference.RetrieveSqlData();
        retrieveSqlData.setFetchUrl(PAGE_JSON_URL);
        retrieveSqlData.setTotal(body.getTotalCount());
        retrieveSqlData.setFilePath(filePath);
        retrieveSqlData.setPreData(entityListToJSONArray(body.getData()));

        DataReference.RetrieveTableData retrieveTableData = new DataReference.RetrieveTableData();
        retrieveTableData.setTableName(tableName);
        retrieveTableData.setDatabaseName(db.getName());
        retrieveTableData.setDataSourceType(db.getDatasourceType());
        retrieveTableData.setDatabaseId(db.getId());
        dealTableDetail(databaseId, tableName, Objects.requireNonNull(DataSourceTypeEnum.of(db.getDatasourceType())), retrieveTableData);

        dataRef.setRetrieveSqlData(retrieveSqlData);
        dataRef.setRetrieveTableDataList(List.of(retrieveTableData));
        return JSON.toJSONString(List.of(dataRef));
    }

    private void dealTableDetail(Long databaseId, String tableName, DataSourceTypeEnum dataSourceTypeEnum, DataReference.RetrieveTableData retrieveTableData) {
        if (dataSourceTypeEnum.equals(DataSourceTypeEnum.DataTable)) {
            String s = tableName.replaceAll("\\D+", "");
            try {
                Long tableId = Long.valueOf(s);
                retrieveTableData.setFileId(tableId);
                TLTableDataDto tlTableDataDto = kbClient.queryTableFileDataByTableId(databaseId, tableId, 1L, 1L);
                retrieveTableData.setTotal(tlTableDataDto.getTotalData());
                retrieveTableData.setFileId(tlTableDataDto.getFileId());

                TLTableDto tlTableDto = kbClient.queryDataTableTableMeta(tableId);
                String businessName = tlTableDto.getBusinessName();
                retrieveTableData.setBusinessTableName(businessName);
            } catch (NumberFormatException e) {
                throw new ApplicationException("table:{}不存在", tableName);
            }

        } else {
            TLTableDataDto tlTableDataDto = kbClient.queryTableData(databaseId, tableName, 1L, 1L);
            retrieveTableData.setTotal(tlTableDataDto.getTotalData());

            TLTableDto tlTableDto = kbClient.queryDirectDBTableMeta(databaseId, tableName);
            String businessName = tlTableDto.getBusinessName();
            retrieveTableData.setBusinessTableName(businessName);
        }
    }

    private JSONArray entityListToJSONArray(List<JsonNode> entityList) {
        JSONArray formattedJson = new JSONArray();
        if (CollectionUtils.isEmpty(entityList)) {
            return formattedJson;
        }
        JSONObject data = new JSONObject();
        JSONArray columns = new JSONArray();
        //columns
        Iterator<String> fieldNames = entityList.get(0).fieldNames();
        while (fieldNames.hasNext()) {
            String key = fieldNames.next();
            JSONObject column = new JSONObject();
            column.put("key", key);
            columns.add(column);
        }
        data.put("columns", columns);
        data.put("data", entityList);
        formattedJson.add(data);
        return formattedJson;
    }

    private List<FilePathDTO> getCurrentFiles(List<String> fileUids, List<FilePathDTO> filePathDTOS) {
        List<FilePathDTO> currentFiles = Lists.newArrayList();
        if (CollectionUtils.isEmpty(filePathDTOS) || CollectionUtils.isEmpty(fileUids))
            return null;
        Map<String, FilePathDTO> fileMap = filePathDTOS.stream().collect(Collectors.toMap(FilePathDTO::getUid, (item -> item)));
        if (!CollectionUtils.isEmpty(fileUids)) {
            fileUids.forEach(uid -> {
                if (!Objects.isNull(fileMap.get(uid))) {
                    currentFiles.add(fileMap.get(uid));
                }
            });
        }
        return currentFiles;
    }

    @Trace
    private ReplyDTO doRunRsForSingleDocument(String s, StringBuffer contentStrBuffer, Answer
            answerObj, AiRequestForSingleDocument aiRequest, AtomicReference<Boolean> isErrFlag, InputType
                                                      inputType, List<SensitiveWordsDTO> sensWordList) {
        log.info("queryId：" + aiRequest.getQueryId() + ",content：" + s);
        ReplyDTO replyDTO = new ReplyDTO();
        replyDTO.setSessionId(aiRequest.getSessionId());
        replyDTO.setQueryId(aiRequest.getQueryId());
        replyDTO.setLastDate(new Date());

        ReplyContentDTO replyContentDTO = new ReplyContentDTO();
        replyContentDTO.setType(MARKDOWN);

        try {
            String answer = "";
            String end = null;
            String docs = null;
            if (StringUtils.isNotEmpty(s)) {
                JSONObject jsonObject = JSON.parseObject(s);
                //获取JSON对象中的值
                answer = jsonObject.getString(ANSWER);
                if (matchSensWord(sensWordList, answer).isPresent()) {
                    log.info("answer:{} contains sensitiveWords", answer);
                    answerObj.setReference(null);
                    throw new ApplicationException(ErrCodeEnum.CONTAINS_SENS_WORD);
                }
                end = jsonObject.getString(END);
                docs = jsonObject.getString(DOCS);
            }

            if (answer != null) {
                replyDTO.setStatus(ReplyStatusEnums.RUN);
                contentStrBuffer.append(answer);
                if (inputType.equals(InputType.MONTAGE)) {
                    replyContentDTO.setContent(contentStrBuffer.toString());
                } else {
                    replyContentDTO.setContent(answer);
                }
                replyDTO.setReply(replyContentDTO);
            } else {
                if (end != null) {
                    replyDTO.setStatus(ReplyStatusEnums.PARSE_SUCCESS);
                    if (isErrFlag.get() == null) {
                        isErrFlag.set(false);
                    }
                    answerObj.setContent(contentStrBuffer.toString());
                    replyDTO.setReference(answerObj.getReference());

                    log.info("queryId：" + aiRequest.getQueryId() + ",content：结束");
                } else {
                    replyDTO.setStatus(ReplyStatusEnums.RUN);
                    if (docs != null) {
                        replyDTO.setReference(docs);
                        answerObj.setReference(docs);
//                        answerDomainService.addOrUpdateAnswerByDialogueIdAndQuestionId(answerObj);
                    }
                }
                if (inputType.equals(InputType.MONTAGE)) {
                    replyContentDTO.setContent(contentStrBuffer.toString());
                } else {
                    replyContentDTO.setContent("");
                }
                replyDTO.setReply(replyContentDTO);
            }
        } catch (ApplicationException e) {
            log.error("ApplicationException:{}", e);
            if (e.getErrCode().equals(ErrCodeEnum.CONTAINS_SENS_WORD.getErrCode())) {
                throw e;
            }
        } catch (Exception e) {
            e.printStackTrace();
            log.error("error:{}", e);
            replyDTO.setStatus(ReplyStatusEnums.PARSE_FAIL);
            if (inputType.equals(InputType.MONTAGE)) {
                replyContentDTO.setContent(contentStrBuffer.toString());
            } else {
                replyContentDTO.setContent("");
            }
            replyContentDTO.setType(MARKDOWN);
            replyDTO.setReply(replyContentDTO);
            isErrFlag.set(true);
            log.error("queryId：" + aiRequest.getQueryId() + ",处理AI异常json：" + e.getLocalizedMessage());
        }
        return replyDTO;
    }

    @Trace
    private ReplyDTO doRunRsForCommonSearch(String s, StringBuffer contentStrBuffer, Answer
            answerObj, CommonSearchRequest commonSearchRequest, AtomicReference<Boolean> isErrFlag, InputType
                                                    inputType, List<SensitiveWordsDTO> sensWordList, String retrieveDocs) {

        ReplyDTO replyDTO = new ReplyDTO();
        replyDTO.setSessionId(commonSearchRequest.getSessionId());
        replyDTO.setQueryId(commonSearchRequest.getQueryId());
        replyDTO.setLastDate(new Date());

        ReplyContentDTO replyContentDTO = new ReplyContentDTO();
        replyContentDTO.setType(MARKDOWN);
        log.info("大模型推理回复结果:{}", s);
        try {
            String answer = "";
            String end = null;
            String docs = null;
            if (StringUtils.isNotEmpty(s)) {
                JSONObject jsonObject = JSON.parseObject(s);
                //获取JSON对象中的值
                answer = jsonObject.getString(ANSWER);
                if (matchSensWord(sensWordList, answer).isPresent()) {
                    log.info("answer:{} contains sensitiveWords", answer);
                    answerObj.setReference(null);
                    throw new ApplicationException(ErrCodeEnum.CONTAINS_SENS_WORD);
                }
                end = jsonObject.getString(END);
                docs = jsonObject.getString(DOCS);
            }

            if (answer != null) {
                replyDTO.setStatus(ReplyStatusEnums.RUN);
                contentStrBuffer.append(answer);
                if (inputType.equals(InputType.MONTAGE)) {
                    replyContentDTO.setContent(contentStrBuffer.toString());
                } else {
                    replyContentDTO.setContent(answer);
                }
                replyDTO.setReply(replyContentDTO);
            } else {
                if (end != null) {
                    replyDTO.setStatus(ReplyStatusEnums.PARSE_SUCCESS);
                    answerObj.setReference(retrieveDocs);
                    if (isErrFlag.get() == null) {
                        isErrFlag.set(false);
                    }

                    answerObj.setContent(contentStrBuffer.toString());
                    answerObj.setReference(JSON.toJSONString(filterDocuments(answerObj.getContent(), answerObj.getReference())));
                    replyDTO.setReference(answerObj.getReference());
                    replyDTO.setDocsTree(answerObj.getReference());
                    log.info("queryId：" + commonSearchRequest.getQueryId() + ",content：结束");
                } else {
                    replyDTO.setStatus(ReplyStatusEnums.RUN);
                    if (docs != null) {
                        replyDTO.setReference(docs);
                        answerObj.setReference(docs);
//                        answerDomainService.addOrUpdateAnswerByDialogueIdAndQuestionId(answerObj);
                    }
                }
                if (inputType.equals(InputType.MONTAGE)) {
                    replyContentDTO.setContent(contentStrBuffer.toString());
                } else {
                    replyContentDTO.setContent("");
                }
                replyDTO.setReply(replyContentDTO);
            }
        } catch (ApplicationException e) {
            log.error("ApplicationException:{}", e);
            if (e.getErrCode().equals(ErrCodeEnum.CONTAINS_SENS_WORD.getErrCode())) {
                throw e;
            }
        } catch (Exception e) {
            e.printStackTrace();
            log.error("error:{}", e);
            replyDTO.setStatus(ReplyStatusEnums.PARSE_FAIL);
            if (inputType.equals(InputType.MONTAGE)) {
                replyContentDTO.setContent(contentStrBuffer.toString());
            } else {
                replyContentDTO.setContent("");
            }
            replyContentDTO.setType(MARKDOWN);
            replyDTO.setReply(replyContentDTO);
            isErrFlag.set(true);
            log.error("queryId：" + commonSearchRequest.getQueryId() + ",处理AI异常json：" + e.getLocalizedMessage());
        }
        return replyDTO;
    }


    private void doFinally(AtomicReference<Boolean> isErrFlag, AiRequest aiRequest, Long
            dialogueId, StringBuffer contentStrBuffer, Answer answerObj) {
//        retriveTags = null;
        if (isErrFlag.get() != null) {
            if (isErrFlag.get().equals(false)) {//正常状态下更新状态
                log.info("queryId：" + aiRequest.getQueryId() + ",content：正常状态修改对话状态");
                dialogueDomainService.updateStatus(dialogueId, StatusEnums.NORMAL);
            }
        }

        answerObj.setContent(contentStrBuffer.toString());
        answerDomainService.addOrUpdateAnswerByDialogueIdAndQuestionId(answerObj);
        log.info("queryId：" + aiRequest.getQueryId() + ",content：完成");
    }


    private QuestionRecommendRequest buildRecommendRequest(Answer answerObj, String query, ModelSimpDTO modelInfo) {
        QuestionRecommendRequest questionRecommendRequest = new QuestionRecommendRequest();
        List<AiHistory> histories = getchatHistory(answerObj.getDialogueId(), 3);
        questionRecommendRequest.setQuery(query);
        questionRecommendRequest.setAnswer(MarkdownUtils.cleanString(answerObj.getContent()));
        questionRecommendRequest.setModelInfo(modelInfo);
        questionRecommendRequest.setChatHistory(histories);
        return questionRecommendRequest;
    }

    private String filterDocs(String content, String reference) {
        Map<String, String> docs = com.alibaba.nacos.shaded.com.google.common.collect.Maps.newHashMap();
        docs.put(DOCUMENTS, "[]");
        docs.put(WEB_DOCUMENTS_LIST, "[]");
        if (reference.contains(WEB_DOCUMENTS_LIST) || reference.contains(DOCUMENTS)) {
            JSONObject refJson = JSONObject.parseObject(reference);
            docs.put(DOCUMENTS, JSON.toJSONString(filterDocuments(content, refJson.getString(DOCUMENTS))));
            docs.put(WEB_DOCUMENTS_LIST, JSON.toJSONString(filterWebDocuments(content, refJson.getString(WEB_DOCUMENTS_LIST))));
        } else
            docs.put(DOCUMENTS, JSON.toJSONString(filterDocuments(content, reference)));
        return JSON.toJSONString(docs);
    }

    private List<WebDocument> filterWebDocuments(String content, String reference) {
        List<WebDocument> newDocs = Lists.newArrayList();
        if (StringUtils.isNotBlank(content) && StringUtils.isNotEmpty(reference)) {
            Set<String> ids = getIdFromContent(content, "(?<=\\[retrive-tag id=\")[^\\\">]+");
            List<WebDocument> documents = JSON.parseArray(reference, WebDocument.class);
            if (!CollectionUtils.isEmpty(ids)) {
                documents.forEach(document -> {
                    if (ids.contains(document.getOrderNum()))
                        newDocs.add(document);
                });
            }
        }
        return newDocs;
    }

    private List<Document> filterDocuments(String content, String reference) {
        List<Document> newDocs = Lists.newArrayList();
        if (StringUtils.isNotBlank(content) && StringUtils.isNotEmpty(reference)) {
            Set<String> ids = getIdFromContent(content, "(?<=\\[retrive-tag id=\")[^\\\">]+");
            List<Document> documents = JSON.parseArray(reference, Document.class);
            if (!CollectionUtils.isEmpty(ids)) {
                documents.forEach(document -> {
                    if (ids.contains(document.getOrderNum()))
                        newDocs.add(document);
                });
            }
        }
        return newDocs;
    }

    public static Set<String> getIdFromContent(String content, String regex) {
        Set<String> result = new HashSet<>();
        Pattern p = Pattern.compile(regex);
        Matcher m = p.matcher(content);
        while (m.find()) {
            result.add(m.group());
        }
        return result;
    }

    private Publisher<? extends ReplyDTO> doErrorResume(AiRequest aiRequest, Exception ex, StringBuffer
            contentStrBuffer, AtomicReference<Boolean> isErrFlag, Config config) {
//        retriveTags = null;
        if (ex instanceof ApplicationException) {
            if (((ApplicationException) ex).getErrCode().equals(ErrCodeEnum.CONTAINS_SENS_WORD.getErrCode())) {
                isErrFlag.set(false);
                return ReplyDTO.fastReply(aiRequest.getSessionId(), aiRequest.getQueryId(), config.getDefaultAnswer(), null).concatWith(Flux.empty());
            }
        }
        ex.printStackTrace();
        log.error("queryId：" + aiRequest.getQueryId() + ",-onErrorResume-" + ex.getMessage());
        String errorMsg = ex.getMessage();
        try {
            Thread.sleep(600);
        } catch (Exception e) {
            log.error("queryId：" + aiRequest.getQueryId() + ",-onErrorResume" + e.getMessage());
            errorMsg = e.getMessage();
        }
        ReplyDTO replyDTO = new ReplyDTO();
        replyDTO.setSessionId(aiRequest.getSessionId());
        replyDTO.setQueryId(aiRequest.getQueryId());
        replyDTO.setLastDate(new Date());
        replyDTO.setStatus(ReplyStatusEnums.PARSE_FAIL);
        ReplyContentDTO replyContentDTO = new ReplyContentDTO();
        replyContentDTO.setContent("模型暂无法返回，请稍后再试!!!");
        replyContentDTO.setType(MARKDOWN);
        replyDTO.setReply(replyContentDTO);
        contentStrBuffer.setLength(0);
        isErrFlag.set(true);
        return Flux.just(replyDTO);
    }

    private Publisher<? extends ReplyDTO> doErrorResumeForSingleDocument(AiRequestForSingleDocument
                                                                                 aiRequest, Exception ex, StringBuffer contentStrBuffer, AtomicReference<Boolean> isErrFlag, Config config) {
        if (ex instanceof ApplicationException) {
            if (((ApplicationException) ex).getErrCode().equals(ErrCodeEnum.CONTAINS_SENS_WORD.getErrCode())) {
                isErrFlag.set(false);
                return ReplyDTO.fastReply(aiRequest.getSessionId(), aiRequest.getQueryId(), config.getDefaultAnswer(), null).concatWith(Flux.empty());
            }
        }
        ex.printStackTrace();
        log.error("queryId：" + aiRequest.getQueryId() + ",-onErrorResume-" + ex.getMessage());
        String errorMsg = ex.getMessage();
        try {
            Thread.sleep(600);
        } catch (Exception e) {
            log.error("queryId：" + aiRequest.getQueryId() + ",-onErrorResume" + e.getMessage());
            errorMsg = e.getMessage();
        }
        ReplyDTO replyDTO = new ReplyDTO();
        replyDTO.setSessionId(aiRequest.getSessionId());
        replyDTO.setQueryId(aiRequest.getQueryId());
        replyDTO.setLastDate(new Date());
        replyDTO.setStatus(ReplyStatusEnums.PARSE_FAIL);
        ReplyContentDTO replyContentDTO = new ReplyContentDTO();
        replyContentDTO.setContent(errorMsg);
        replyContentDTO.setType(MARKDOWN);
        replyDTO.setReply(replyContentDTO);
        contentStrBuffer.setLength(0);
        isErrFlag.set(true);
        return Flux.just(replyDTO);
    }

    private Publisher<? extends ReplyDTO> doErrorResumeForCommonSearch(CommonSearchRequest
                                                                               commonSearchRequest, Exception ex, StringBuffer contentStrBuffer, AtomicReference<Boolean> isErrFlag, Config
                                                                               config) {
        if (ex instanceof ApplicationException) {
            if (((ApplicationException) ex).getErrCode().equals(ErrCodeEnum.CONTAINS_SENS_WORD.getErrCode())) {
                isErrFlag.set(false);
                return ReplyDTO.fastReply(commonSearchRequest.getSessionId(), commonSearchRequest.getQueryId(), config.getDefaultAnswer(), null).concatWith(Flux.empty());
            }
        }
        ex.printStackTrace();
        log.error("queryId：" + commonSearchRequest.getQueryId() + ",-onErrorResume-" + ex.getMessage());
        String errorMsg = ex.getMessage();
        try {
            Thread.sleep(600);
        } catch (Exception e) {
            log.error("queryId：" + commonSearchRequest.getQueryId() + ",-onErrorResume" + e.getMessage());
            errorMsg = e.getMessage();
        }
        ReplyDTO replyDTO = new ReplyDTO();
        replyDTO.setSessionId(commonSearchRequest.getSessionId());
        replyDTO.setQueryId(commonSearchRequest.getQueryId());
        replyDTO.setLastDate(new Date());
        replyDTO.setStatus(ReplyStatusEnums.PARSE_FAIL);
        ReplyContentDTO replyContentDTO = new ReplyContentDTO();
        replyContentDTO.setContent(errorMsg);
        replyContentDTO.setType(MARKDOWN);
        replyDTO.setReply(replyContentDTO);
        contentStrBuffer.setLength(0);
        isErrFlag.set(true);
        return Flux.just(replyDTO);
    }


    /**
     * 模型推理数据组装json
     *
     * @param dialogueId
     * @param jsonObject
     * @return
     */
    private JSONObject modelBasedInferenceParamToJson(Long dialogueId, JSONObject jsonObject) {
        log.info("question.getDialogueId()--" + dialogueId);
        String knowledge_base_name = (String) jsonObject.get(KNOWLEDGE_BASE_NAME);
        if (Objects.nonNull(knowledge_base_name)) {
            jsonObject.put(KNOWLEDGE_BASE_NAME, knowledge_base_name.split(";"));
        }
        Integer maxRound = jsonObject.getInteger(MAX_ROUND);
        jsonObject.put(CHAT_HISTORY, getchatHistory(dialogueId, maxRound));
        jsonObject.put(STREAM, true);
        return jsonObject;
    }


    private ExtendedConfig modelBasedInferenceParamToJsonRe(Long dialogueId, ExtendedConfig
            config, List<FilePathDTO> filePathDTOS, List<Document> documents, List<WebDocument> webDocumentList, SqlMetaData
                                                                    sqlMetaData) {
        try {
            ExtendedConfig newConfig = (ExtendedConfig) config.clone();
            newConfig.setDocuments(documents, webDocumentList);
            log.info("question.getDialogueId()--" + dialogueId);
            StringBuffer stringBuffer = new StringBuffer();
            stringBuffer.append(config.getQuery());
            if (CollectionUtils.isEmpty(filePathDTOS)) {
                //正常的知识库
                newConfig.convertKBN2Array();
            } else {
                //文档上传问答,将解析后的结果存储在redis中
                cacheFiles(filePathDTOS);
                //设置文件信息同时删除知识库信息
                newConfig.setFilePathsAndRemoveKb(filePathDTOS.stream().map(FilePathDTO::getTxtFilePath).collect(Collectors.toList()));
            }
            Integer maxRound = config.getMaxRound();
            List<AiHistory> historyMapList = getchatHistory(dialogueId, maxRound);
            newConfig.setChatHistory(historyMapList);
            newConfig.setStream(true);
            if (Objects.nonNull(sqlMetaData) && Objects.nonNull(sqlMetaData.getTableResultData())) {
                newConfig.setDatabaseDocuments(sqlMetaData.getDatabaseDocuments());
                newConfig.setTableResultData(sqlMetaData.getTableResultData());
            }

            newConfig.removeFields(Arrays.asList(ISDEL, TOP_K, TOP_P, RERANK, STATUS, PROLOGUE, MAX_ROUND, DEPENDONKB, MODEL_NAME, CONFIG_NAME, ENABLED_FAQ, IS_DOWNLOAD, DEFAULTANSWER, ENABLED_GRAPH, ENABLED_RERANK, SCORE_THRESHOLD, KNOWLEDGE_BASE_NAME, ENABLED_TABLE_SELECT, THINKING, KNOWLEDGE_BASE_NAME_SOURCE, ENABLE_WEB_SEARCH, SELECTED_KNOWLEDGE_BASE, SEARCH_POLICY, RERANK_MODEL_NAME));
            return newConfig;
        } catch (CloneNotSupportedException ex) {
            throw new ApplicationException("build params error...");
        }
    }

    private ExtendedConfig buildInferenceParamForSingleDocument(ExtendedConfig
                                                                        config, List<AiRequestForSingleDocument.qaPair> qaHistory) {
        try {
            ExtendedConfig newConfig = (ExtendedConfig) config.clone();
            StringBuffer stringBuffer = new StringBuffer();
            stringBuffer.append(config.getQuery());
            newConfig.convertKBN2Array();

            List<AiHistory> historyMapList = new ArrayList<>();
            for (AiRequestForSingleDocument.qaPair onePair : qaHistory) {
                stringBuffer.append(onePair.getQuery());
                //删除a标签和换行
                String answerContent = onePair.getAnswer().replaceAll("<a.*?</a>", "").replaceAll("\n", "");
                stringBuffer.append(answerContent);
                if (stringBuffer.length() > nacosConfig.getRequestLengthLimit()) {
                    break;
                }
                AiHistory userHistory = new AiHistory();
                userHistory.setQuery(onePair.getQuery());
                userHistory.setAnswer(answerContent);
                historyMapList.add(userHistory);
            }
            newConfig.setChatHistory(historyMapList);
            newConfig.setStream(true);
            return newConfig;
        } catch (CloneNotSupportedException ex) {
            throw new ApplicationException("build params error...");
        }
    }

    private JSONObject modelBasedInferenceParamToJsonForCZBank(JSONObject jsonObject) {
        String knowledge_base_name = (String) jsonObject.get(KNOWLEDGE_BASE_NAME);
        if (Objects.nonNull(knowledge_base_name)) {
            jsonObject.put(KNOWLEDGE_BASE_NAME, knowledge_base_name.split(";"));
        }
        jsonObject.put(STREAM, false);
        return jsonObject;
    }

    /**
     * 检索召回组装json数据
     *
     * @param extendedConfig
     * @return
     */
    private ExtendedConfig retrieveRecallParamToJson(ExtendedConfig extendedConfig) throws ApplicationException {
        ExtendedConfig newConfig;
        try {
            newConfig = (ExtendedConfig) extendedConfig.clone();
        } catch (CloneNotSupportedException ex) {
            throw new ApplicationException("params build error..");
        }
        newConfig.setKnowledgeBaseName(extendedConfig.getKnowledgeBaseName());
        newConfig.convertKBN2Array();
        newConfig.setStream(false);
        newConfig.setTopN();
        newConfig.removeFields(Arrays.asList(ISDEL, STATUS, PROLOGUE, THINKING, MAX_ROUND, DEPENDONKB, MODEL_NAME, CONFIG_NAME, IS_DOWNLOAD, DEFAULTANSWER, SYSTEM_PROMPT, NEED_TRACE_SOURCE, RERANK_MODEL_NAME, KNOWLEDGE_BASE_NAME_SOURCE, ENABLE_THINKING, MODEL_INFO, MULTI_MODEL_INFO, STREAM, RECOMMEND_MODEL_NAME, PLAN_MODEL_NAME));
        return newConfig;
    }

    private JSONObject retrieveRecallParamToJson(JSONObject jsonObject) {
        JSONObject newJsonObject = jsonObject.clone();
        String knowledge_base_name = (String) jsonObject.get(KNOWLEDGE_BASE_NAME);
        newJsonObject.put(KNOWLEDGE_BASE_NAME, knowledge_base_name.split(";"));
        newJsonObject.put(STREAM, false);
        return newJsonObject;
    }


    @Override
    public KnowledgeDTO knowledge(AiRequest aiRequest) {
        log.info("knowledgeRequest:" + aiRequest.toString());
        Long dialogueId = dialogueDomainService.addAndGetIdBySessionId(aiRequest.getSessionId(), aiRequest.getSysType());
        // TODO: 2024/7/23 从对话信息里拿 added by liutaiyun
        Dialogue dialogue = dialogueDomainService.getDialogueById(dialogueId);
        Config config = dialogue.getConfig();
        if (Objects.isNull(config)) {
            config = searchConfigDomainService.getDefaultConfig();
        }
        if (config == null) {
            KnowledgeDTO knowledgeDTO = new KnowledgeDTO();
            knowledgeDTO.setSessionId(aiRequest.getSessionId());
            knowledgeDTO.setQueryId(aiRequest.getQueryId());
            knowledgeDTO.setLastDate(new Date());
            knowledgeDTO.setFilePath(nacosConfig.getMinioUrl());
            knowledgeDTO.setStatus(ReplyStatusEnums.PARSE_SUCCESS);
            knowledgeDTO.setContent("[]");
            return knowledgeDTO;
        }
        String jsonString = config.getConfigJson();
        JSONObject jsonConfig = JSON.parseObject(jsonString);
        jsonConfig.put(QUERY, aiRequest.getContent());
        JSONObject alParams = retrieveRecallParamToJson(jsonConfig);

        KnowledgeDTO knowledgeDTO = new KnowledgeDTO();
        knowledgeDTO.setSessionId(aiRequest.getSessionId());
        knowledgeDTO.setQueryId(aiRequest.getQueryId());
        knowledgeDTO.setLastDate(new Date());
        knowledgeDTO.setFilePath(nacosConfig.getMinioUrl());

        String rs = retrieveRecall(aiRequest, alParams, dialogueId, Boolean.TRUE);
        if (Objects.nonNull(rs)) {
            knowledgeDTO.setStatus(ReplyStatusEnums.PARSE_SUCCESS);
            knowledgeDTO.setContent(rs);
        } else {
            knowledgeDTO.setStatus(ReplyStatusEnums.PARSE_FAIL);
            knowledgeDTO.setContent("");
        }
        log.info("完成");
        return knowledgeDTO;
    }

    /**
     * 1.调用检索召回接口（）
     *
     * @param aiRequest
     * @param alParams
     * @param dialogueId
     * @return
     */
    @Trace
    private String retrieveRecall(AiRequest aiRequest, JSONObject alParams, Long dialogueId, Boolean isQuery) {
        JSONObject retrieveRecallParam = new JSONObject();
        retrieveRecallParam.put(QUERY, alParams.getString(QUERY));
        retrieveRecallParam.put(KNOWLEDGE_BASE_NAME, alParams.getJSONArray(KNOWLEDGE_BASE_NAME));
        retrieveRecallParam.put(TOP_K, alParams.getString(TOP_K));
        retrieveRecallParam.put(ENABLED_RERANK, alParams.getString(ENABLED_RERANK));
        retrieveRecallParam.put(ENABLED_FAQ, alParams.getString(ENABLED_FAQ));
        Question question = BeanUtil.copyProperties(alParams, Question.class);
        question.setKnowledgeParams(retrieveRecallParam.toJSONString());
        question.setAlgModel(String.valueOf(alParams.get(MODEL_NAME)));
        question.setContent(aiRequest.getContent());
        question.setType(aiRequest.getType());
        question.setFrontUuid(aiRequest.getQueryId());
        question.setAudioUrl(aiRequest.getAudioUrl());
        question.setDialogueId(dialogueId);
        Long questionId = questionDomainService.addOrUpdateQuestionByDialogueIdAndFrontUuid(question);
        if (isQuery) {
            Answer answer = answerDomainService.getAnswerByDialogueIdAndQuestionId(dialogueId, questionId);
            if (answer != null && StringUtils.isNotBlank(answer.getReference())) {
                return answer.getReference();
            }
        }
        String rs;
        try {
            JSONObject config = BeanUtil.copyProperties(alParams, JSONObject.class);
            config.remove(SCORE_THRESHOLD);
            log.info("retrieveRecall-检索召回请求参数:" + JSON.toJSONString(config));
            HttpEntity httpEntity = new HttpEntity(alParams);
            long startTime = System.currentTimeMillis();
            rs = restTemplate.postForObject(nacosConfig.getSearchDocsUrl(), httpEntity, String.class);
            log.info("knowledge---getBody:" + rs);
            long endTime = System.currentTimeMillis();

            log.info("耗时：{}ms", endTime - startTime);
            JSONObject jsonObject = JSON.parseObject(rs);
            JSONObject dataJson = jsonObject.getJSONObject(DATA);
//            List<JSONObject> documentsList = dataJson.getList(DOCUMENTS_LIST, JSONObject.class);
//            String logList = dataJson.getString(LOG_LIST);
            rs = dataJson.getString(DOCUMENTS_LIST);

//            Answer answer = new Answer();
//            answer.setLogResult(logList);
//            answer.setReference(setParsedFilePaths(documentsList));
//            answer.setType(aiRequest.getType());
//            answer.setDialogueId(dialogueId);
//            answer.setQuestionId(questionId);
//            answerDomainService.addOrUpdateAnswerByDialogueIdAndQuestionId(answer);
        } catch (Exception e) {
            log.error("queryId：" + aiRequest.getQueryId() + ",-knowledge-" + e.getMessage());
            rs = null;
        }
        return rs;

    }

    private RetrievedData retrieveRecall(AiRequest aiRequest, ExtendedConfig alParams, Long dialogueId, Boolean
            isQuery) {
        try {
            JSONObject config = BeanUtil.copyProperties(alParams.getConfig(), JSONObject.class);
            if (config.containsKey(DATABASE_NAME) && !config.getJSONArray(DATABASE_NAME).isEmpty()) {
                config.put(ENABLE_DATABASE, true);
                String[] databaseName = config.getJSONArray(DATABASE_NAME).stream()
                        .map(o -> ((JSONObject) o).getString("key"))
                        .toArray(String[]::new);
                config.put(DATABASE_NAME, databaseName);
            }
            if (config.containsKey(SELECTED_KNOWLEDGE_BASE) && !config.getJSONArray(SELECTED_KNOWLEDGE_BASE).isEmpty()) {
                return combineRetrieveDataList(buildRetrieveDataList(alParams.getConfig()));
            } else {
                log.info("retrieveRecall-检索召回请求参数:{}", JSON.toJSONString(config));
                HttpHeaders headers = new HttpHeaders();
                headers.setContentType(MediaType.APPLICATION_JSON);
                HttpEntity<String> httpEntity = new HttpEntity<>(JSON.toJSONString(config), headers);
                String rs = restTemplate.postForObject(nacosConfig.getSearchDocsUrl(), httpEntity, String.class);
                log.info("knowledge---getBody:" + rs);
                RetrievedData retrievedData = RetrievedData.getDefault(rs);
                return retrievedData;
            }

        } catch (Exception e) {
            log.error("queryId：" + aiRequest.getQueryId() + ",-knowledge-" + e.getMessage());
            return null;
        }

    }

    private SqlMetaData retrieveSqlData(Config config, String query, Long dialogueId, RetrievedData retrievedData) {
        JSONObject helperConfig = JSON.parseObject(config.getConfigJson());
        RetrieveData retrieveData = JSONObject.parseObject(retrievedData.getData().toJSONString(), RetrieveData.class);
        //配置助手中有配置数据库才召回
        if (helperConfig.containsKey(DATABASE_NAME) && !helperConfig.getJSONArray(DATABASE_NAME).isEmpty()) {
            //1.召回sql
            ModelSimpDTO simpByModeName = getModelSimpDTO(helperConfig.getString(MODEL_NAME));
            SqlMetaData sqlMetaData = new SqlMetaData();
            sqlMetaData.setDatabaseDocuments(retrieveData.getDatabaseDocuments());
            SqlGenerateRequest sqlGenerateRequest = SqlGenerateRequest.from(query, retrieveData.getDatabaseDocuments(), simpByModeName);
            log.info("execute sql retrieve params:{}", JSON.toJSONString(sqlGenerateRequest));
            try {
                LLMClientResp<RetrieveSql> result = llmClient.llmSqlGenerate(sqlGenerateRequest);
                log.info("result code:{}", result.getCode());
                if (result.getCode() == 200) {
                    QueryDataReq queryDataReq = QueryDataReq.from(result.getData().getSql(), result.getData().getDatabaseId(), dialogueId);
                    log.info("queryDataReq:{}", JSON.toJSONString(queryDataReq));
                    //查询sql并持久化到minio
                    try {
                        List<Entity> entities = kbClient.queryData(queryDataReq);

                        if (!CollectionUtils.isEmpty(entities)) {
                            int rowCount = entities.size();
                            int columnCount = entities.get(0).keySet().size();
                            List<Entity> subList = entities.subList(0, Math.min(rowCount, FIRST_N_ROW));
                            SqlMetaData.TableResultData tableResultData = new SqlMetaData.TableResultData();
                            tableResultData.setRowCount(rowCount);
                            tableResultData.setColumnCount(columnCount);
                            tableResultData.setHeadNRow(subList);
                            sqlMetaData.setTableResultData(tableResultData);
                        }
                        log.info("kbClient.queryData...{}", JSON.toJSONString(entities));
                        RetrieveSqlDataReference dataReference = appendSqlDataToAnswer(result.getData(), dialogueId);
                        sqlMetaData.setRetrieveSqlDataReference(dataReference);
                        return sqlMetaData;
                    } catch (Exception e) {
                        log.error("query sql data error occurred", e);
                    }
                } else {
                    log.error("something wrong with retrieving sql data...:{}", result.getMsg());
                }
            } catch (Exception e) {
                log.error("execute sql retrieve failed!!", e);
            }
        }
        return null;
    }


    private ModelSimpDTO getModelSimpDTO(String modelName) {
        String modelCacheKey = "model-info:" + modelName;
        ModelSimpDTO simpByModeName = null;
        if (!redissonUtils.exists(modelCacheKey)) {
            simpByModeName = modelClient.getSimpByModeName(modelName);
            redissonUtils.set(modelCacheKey, JSON.toJSONString(simpByModeName), 3L, TimeUnit.HOURS);
        } else {
            log.info("model-info hit redis key:{}", modelCacheKey);
            simpByModeName = JSON.parseObject((String) redissonUtils.get(modelCacheKey), ModelSimpDTO.class);
        }
        if (Objects.isNull(simpByModeName)) {
            throw new ApplicationException(ErrCodeEnum.MODEL_NOT_EXIST);
        }
        return simpByModeName;
    }


    private List<RetrievedData> buildRetrieveDataList(JSONObject config) {
        JSONObject configCopy = JSONObject.parseObject(config.toJSONString());
        JSONArray selectedKnowledgeBase = configCopy.getJSONArray(SELECTED_KNOWLEDGE_BASE);
        CountDownLatch latch = new CountDownLatch(selectedKnowledgeBase.size());
        List<RetrievedData> retrievedDataList = Lists.newArrayList();
        for (int i = 0; i < selectedKnowledgeBase.size(); i++) {
            JSONObject oneKnowledgeBase = selectedKnowledgeBase.getJSONObject(i);
            JSONArray labels = oneKnowledgeBase.getJSONArray(LABELS);
            JSONObject conditionJson = new JSONObject();
            conditionJson.put(LABELS, labels);
            configCopy.put(KNOWLEDGE_BASE_NAME, new JSONArray(oneKnowledgeBase.getString(NAME)));
            configCopy.put(CONDITION_LOGIC_OPERATIONS, OR);
            configCopy.put(CONDITION_JSON, conditionJson);
            //开启线程
            asyncExecutor.execute(() -> {
                try {
                    log.info("retrieveRecall-检索召回请求参数:{}", JSON.toJSONString(config));
                    HttpEntity httpEntity = new HttpEntity(configCopy);
                    String rs = restTemplate.postForObject(nacosConfig.getSearchDocsUrl(), httpEntity, String.class);
                    log.info("knowledge---getBody:" + rs);
                    RetrievedData retrievedData = RetrievedData.getDefault(rs);
                    retrievedDataList.add(retrievedData);
                } finally {
                    latch.countDown();
                }
            });
        }
        try {
            latch.await();
            log.info("asyncExecutor:selectedKnowledgeBase:retrieve:ok");
        } catch (InterruptedException e) {
            throw new RuntimeException(e);
        }
        return retrievedDataList;
    }

    private RetrievedData combineRetrieveDataList(List<RetrievedData> retrievedDataList) {
        JSONArray documentStringList = new JSONArray();
        JSONArray faqStringList = new JSONArray();
        JSONArray logStringList = new JSONArray();
        retrievedDataList.forEach(retrievedData -> {
            JSONArray documentsList = retrievedData.getData().getJSONArray(DOCUMENTS_LIST);
            documentStringList.addAll(documentsList);
            JSONArray faqResultList = retrievedData.getData().getJSONArray(FAQ_RESULT_LIST);
            faqStringList.addAll(faqResultList);
            JSONArray logList = retrievedData.getData().getJSONArray(LOG_LIST);
            logStringList.addAll(logList);
        });
        RetrievedData retrievedData = new RetrievedData();
        JSONObject data = new JSONObject();
        data.put(DOCUMENTS_LIST, documentStringList);
        data.put(FAQ_RESULT_LIST, faqStringList);
        data.put(LOG_LIST, logStringList);
        retrievedData.setData(data);
        return retrievedData;
    }


    private RetrievedData retrieveRecallForSingleDocument(AiRequestForSingleDocument aiRequest, ExtendedConfig
            alParams) {
        try {
            JSONObject config = BeanUtil.copyProperties(alParams.getConfig(), JSONObject.class);
            config.remove(SCORE_THRESHOLD);
            JSONObject doc = new JSONObject();
            doc.put(TITLE, Arrays.asList(aiRequest.getDocumentTitle()));
            config.put(CONDITION_JSON, doc);
            config.put(CHAT_HISTORY, aiRequest.getQaHistory());
            log.info("单文档召回请求参数:{}", JSONObject.toJSONString(config));
            HttpEntity httpEntity = new HttpEntity(config);
            String rs = restTemplate.postForObject(nacosConfig.getSearchDocsUrl(), httpEntity, String.class);
            log.info("单文档召回响应:{}", rs);
            RetrievedData retrievedData = RetrievedData.getDefault(rs);
            return retrievedData;
        } catch (Exception e) {
            log.error("queryId：" + aiRequest.getQueryId() + ",-knowledge-" + e.getMessage());
            return null;
        }
    }

    private RetrievedData retrieveRecallForCommonSearch(CommonSearchRequest commonSearchRequest, ExtendedConfig
            alParams) {
        try {
            JSONObject config = BeanUtil.copyProperties(alParams.getConfig(), JSONObject.class);
            config.remove(SCORE_THRESHOLD);
            log.info("retrieveRecall-检索召回请求参数:{}", JSON.toJSONString(config));
            HttpEntity httpEntity = new HttpEntity(alParams.getConfig());
            String rs = restTemplate.postForObject(nacosConfig.getSearchDocsUrl(), httpEntity, String.class);
            log.info("knowledge---getBody:" + rs);
            RetrievedData retrievedData = RetrievedData.getDefault(rs);
            rs = retrievedData.getDocumentString();
            return retrievedData;
        } catch (Exception e) {
            log.error("queryId：" + commonSearchRequest.getQueryId() + ",-knowledge-" + e.getMessage());
            return null;
        }

    }

    private String getParsedFilePath(JSONObject metadata) {
        if (Objects.isNull(metadata)) {
            return null;
        }
        String source = metadata.getString(SOURCE);
        String fileName = source.substring(source.lastIndexOf("/") + 1);
        String filePath = "";
        try {
            filePath = storageProperties.getDefaultStorageProperties().getEndPoint() + "/" + source.substring(0, source.lastIndexOf("/")) + "/parsed/" + fileName + TXT;
        } catch (Exception e) {
            log.error(e.getMessage());
        }
        return filePath;
    }

    private String retrieveRecallForCZBank(AiCZBankRequest aiRequest, JSONObject alParams) {
        log.info("retrieveRecall-检索召回请求参数:" + alParams);
        String rs;
        try {
            HttpEntity httpEntity = new HttpEntity(alParams);
            rs = restTemplate.postForObject(nacosConfig.getSearchDocsUrl(), httpEntity, String.class);
            JSONObject jsonObject = JSON.parseObject(rs);
            JSONObject dataJson = jsonObject.getJSONObject(DATA);
            rs = dataJson.getString(DOCUMENTS_LIST);
        } catch (Exception e) {
            log.error("retrieveRecall-检索召回出现异常" + e.getMessage());
            rs = null;
        }
        return rs;

    }

    @Override
    public Flux<ReplyDTO> questionRe(AiRequest aiRequest) {
        log.info("questionReRequest:" + aiRequest.toString());
        return publicQuestionRe(aiRequest, InputType.SEPARATE);
    }

    @Override
    public String[] recommendQuestion(String queryId, Long configId) {
        //查询助手配置
        Config config = searchConfigDomainService.getConfigById(configId);
        Boolean permission = Objects.nonNull(config) && config.getCreateBy().equals(UserContext.getUser().getUserName());
        //判断是否有数据权限
        if (!permission && Objects.nonNull(config))
            permission = authClient.isPermission(PrivilegeTypeEnums.INDEX_CONF.getCode(), configId);
        //如果没有权限查询自己默认的助手配置
        if (!permission) {
            config = searchConfigDomainService.getDefaultConfig();
            //如果自己没有默认的助手配置,使用系统默认助手配置
            if (Objects.isNull(config)) {
                String defaultConf = nacosConfig.getDefaultSearchConf();
                config = new Config();
                config.setConfigJson(defaultConf);
            }
        }
        JSONObject configJson = JSON.parseObject(config.getConfigJson());
        ModelSimpDTO modelInfo = modelClient.getSimpByModeName(configJson.getString(RECOMMEND_MODEL_NAME));

        log.info("recommendQuestion...");
        Answer answer = answerDomainService.getAnswerByQueryId(queryId);
        Question question = questionDomainService.getQuestionById(answer.getQuestionId());
        QuestionRecommendRequest questionRecommendRequest = buildRecommendRequest(answer, question.getContent(), modelInfo);
        log.info("questionRecommendRequest:{}", JSON.toJSONString(questionRecommendRequest));
        String[] strings = llmClient.llmQuestionRecommend(questionRecommendRequest);
        answer.setRecommendQuestion(JSON.toJSONString(strings));
        answerDomainService.addOrUpdateAnswerByDialogueIdAndQuestionId(answer);
        return ArrayUtil.isEmpty(strings) ? new String[0] : strings;
    }

    @Override
    public Flux<ReplyDTO> questionForSingleDocument(AiRequestForSingleDocument aiRequest) {
        return publicQuestionForSingleDocument(aiRequest, InputType.SEPARATE);
    }

    @Override
    public List<Map> getAiModelNames() {
        List<Map> mapList = JSON.parseArray(nacosConfig.getSelectModelNames(), Map.class);
        return mapList;
    }

    private String dateString() {
        LocalDate currentDate = LocalDate.now();
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd");
        String formattedDate = currentDate.format(formatter);
        return formattedDate;
    }

    @Override
    public MinioAudioVTO audioUploadAndIdentify(MultipartFile file) {
        MinioAudioVTO minioAudioVTO = new MinioAudioVTO();
        String folder = "audio/" + UserContext.getUser().getUserName() + "/" + dateString() + "/" + System.currentTimeMillis() + "/";
        try {
            //批量上传文件
            FileInfo fileInfo = fileStorageUtils.putObject(folder, file, null);
            minioAudioVTO.setAudioUrl(fileInfo.getFilePath());
        } catch (FileStorageException ex) {
            log.error(ex.getMessage(), ex);
            throw new ApplicationException(ErrCodeEnum.PUT_OBJECT_ERROR);
        }

        try {

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.MULTIPART_FORM_DATA);
            MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
            Path tempFilePath = Files.createTempFile(PREFIX, SUFFIX);
            Files.copy(file.getInputStream(), tempFilePath, StandardCopyOption.REPLACE_EXISTING);
            FileSystemResource resource = new FileSystemResource(tempFilePath.toFile());
            body.add(FILE, resource);
            HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);

            ResponseEntity<String> rs = restTemplate.exchange(nacosConfig.getAudioIdentifyUrl(), HttpMethod.POST, requestEntity, String.class);
            // 转换为具体类型的List
            List<Map> itemList = JSON.parseArray(rs.getBody(), Map.class);
            if (itemList.size() > 0) {
                minioAudioVTO.setContent(String.valueOf(itemList.get(0).get(TEXT)));
            }
        } catch (Exception ex) {
            log.error(ex.getMessage(), ex);
            throw new ApplicationException(ErrCodeEnum.SPEECH_RECOGNITION_ERROR);
        }
        return minioAudioVTO;
    }

    @Override
    public Boolean addOrUpdateQuestionAndAnswer(QuestionAndAnswerAddReq questionAndAnswerAddReq) {
        Config config = searchConfigDomainService.getConfigById(questionAndAnswerAddReq.getConfigId());
        if (config == null) {
            throw new ApplicationException(ErrCodeEnum.NO_SEARCH_CONFIG);
        }
        String configJson = config.getConfigJson();
        JSONObject configJsonObject = JSONObject.parse(configJson);
        String modelName = configJsonObject.getString(MODEL_NAME);
        String knowledgeBaseName = configJsonObject.getString(KNOWLEDGE_BASE_NAME);
        Dialogue dialogue = dialogueDomainService.getDialogueBySessionId(questionAndAnswerAddReq.getSessionId());
        if (dialogue == null) {
            throw new ApplicationException(ErrCodeEnum.DIALOG_NOT_EXISTS_ERROR);
        }

        Question question = Question.builder()
                .gmtCreate(questionAndAnswerAddReq.getLastDate())
                .gmtModified(questionAndAnswerAddReq.getLastDate())
                .dialogueId(dialogue.getId())
                .content(questionAndAnswerAddReq.getQuestionContent())
                .type(TEXT)
                .frontUuid(questionAndAnswerAddReq.getQueryId())
                .algModel(StringUtils.isEmpty(questionAndAnswerAddReq.getAlgModel()) ? modelName : questionAndAnswerAddReq.getAlgModel())
                .algParams(configJson)
                .knowledgeBaseName(knowledgeBaseName)
                .build();
        Long questionId = questionDomainService.addOrUpdateQuestionByDialogueIdAndFrontUuid(question);

        Answer answer = Answer.builder()
                .gmtCreate(questionAndAnswerAddReq.getLastDate())
                .gmtModified(questionAndAnswerAddReq.getLastDate())
                .dialogueId(dialogue.getId())
                .questionId(questionId)
                .content(questionAndAnswerAddReq.getAnswerContent())
                .type(TEXT)
                .build();
        return answerDomainService.addOrUpdateAnswerByDialogueIdAndQuestionId(answer);
    }

    @Override
    public Flux<ReplyDTO> commonSearch(CommonSearchRequest commonSearchRequest) {
        return publicCommonSearch(commonSearchRequest, InputType.SEPARATE);
    }

    private Flux<ReplyDTO> publicCommonSearch(CommonSearchRequest commonSearchRequest, InputType inputType) {
        String sessionId = commonSearchRequest.getSessionId();
        String queryId = commonSearchRequest.getQueryId();

        Config config = searchConfigDomainService.getConfigById(commonSearchRequest.getConfigId());
        if (Objects.isNull(config)) {
            //个人的默认助手配置
            config = searchConfigDomainService.getDefaultConfig();
            //系统默认助手配置
            if (Objects.isNull(config)) {
                String defaultConf = nacosConfig.getDefaultSearchConf();
                config = new Config();
                config.setConfigJson(defaultConf);
            }
        }

        // 检索召回+推理（解决流式问题）
        ExtendedConfig extendedConfig = new ExtendedConfig();
        List<SensitiveWordsDTO> sensWordList = Lists.newArrayList();
        ExtendedConfig alParams;
        List<Document> documents = new ArrayList<>();
        List<Document> webRsDocuments = new ArrayList<>();

        RetrievedData retrievedData = null;
        //组装请求参数
        buildConfig(config, true, false);
        extendedConfig.init(config.getConfigJson());
        extendedConfig.setQuery(commonSearchRequest.getContent());

        //获取敏感词
        sensWordList = getSensitiveWordsByIds(config.getSensitiveWordIds());
        //对问题进行分词，如果有敏感词，则直接返回通用回答
        if (matchSensWord(sensWordList, commonSearchRequest.getContent()).isPresent()) {
            String answer = config.getDefaultAnswer();
            //如果问题命中敏感词，则返回配置的默认回复
            return ReplyDTO.fastReplyRe(sessionId, queryId, answer, null, AIResultTypeEnum.SENSITIVE_WORDS.getCode());
        }

        if (Objects.nonNull(extendedConfig.getKnowledgeBaseName())) {
            //检索召回组装json数据
            alParams = retrieveRecallParamToJson(extendedConfig);
            //1.调用检索召回接口
            retrievedData = retrieveRecallForCommonSearch(commonSearchRequest, alParams);
            if (Objects.nonNull(retrievedData)) {
                documents.addAll(retrievedData.getSimpleDocuments(storageProperties.getDefaultStorageProperties().getEndPoint()));
                List<Document> fullDocuments = retrievedData.getDocuments(storageProperties.getDefaultStorageProperties().getEndPoint());
                webRsDocuments.addAll(fullDocuments);
            }
        }

        //如果助手配置了强关联知识库,且知识库没有召回内容，则直接返回
        if (Objects.nonNull(config.getDependOnKb()) && config.getDependOnKb() == 1 && (Objects.isNull(retrievedData) || !retrievedData.existDocs())) {
            //保存问题和答案
            String answer = "抱歉未能找到您要的答案";
            return ReplyDTO.fastReplyRe(sessionId, queryId, answer, null);
        }

        alParams = buildInferenceParamForCommonSearch(extendedConfig);
        if (Objects.nonNull(retrievedData))
            alParams.setDocuments(JSON.parseArray(retrievedData.getDocumentString(), Document.class), null);

        //2.大模型推理服务
        return modelBasedInferenceReForCommonSearch(webRsDocuments, commonSearchRequest, alParams, inputType, sensWordList, config);
    }

    private ExtendedConfig buildInferenceParamForCommonSearch(ExtendedConfig config) {
        try {
            ExtendedConfig newConfig = (ExtendedConfig) config.clone();
            StringBuffer stringBuffer = new StringBuffer();
            stringBuffer.append(config.getQuery());
            newConfig.convertKBN2Array();
            newConfig.setStream(true);
            String modelName = newConfig.getConfig().getString(MODEL_NAME);
            newConfig.getConfig().put(MODEL_INFO, modelClient.getSimpByModeName(modelName));
            return newConfig;
        } catch (CloneNotSupportedException ex) {
            throw new ApplicationException("build params error...");
        }
    }

    private Flux<ReplyDTO> modelBasedInferenceReForCommonSearch(List<Document> docs, CommonSearchRequest
            commonSearchRequest, ExtendedConfig alParams, InputType
                                                                        inputType, List<SensitiveWordsDTO> sensWordList, Config config) {
        log.info("modelBasedInference--模型推理请求参数:" + alParams.getConfig());
        String sessionId = commonSearchRequest.getSessionId();
        String queryId = commonSearchRequest.getQueryId();
        StringBuffer contentStrBuffer = new StringBuffer();

        String webRsDocuments = JSON.toJSONString(docs);
        Answer answerObj = new Answer();
        answerObj.setType(commonSearchRequest.getType());
        AtomicReference<Boolean> isErrFlag = new AtomicReference<>(null);
        Flux<ReplyDTO> thirdPartyStream = webLlmOpenChatClient.post()
                .uri(nacosConfig.getLlmOpenChatUrl())
                .contentType(MediaType.APPLICATION_JSON)
                .body(BodyInserters.fromValue(alParams.getConfigJSONString())) //参数
                .accept(MediaType.TEXT_EVENT_STREAM) //接收text/event-stream流的数据
                .retrieve()
                .bodyToFlux(String.class) //输出格式
                .map(s -> doRunRsForCommonSearch(s, contentStrBuffer, answerObj, commonSearchRequest, isErrFlag, inputType, sensWordList, webRsDocuments))
                .onErrorResume(Exception.class, ex -> doErrorResumeForCommonSearch(commonSearchRequest, ex, contentStrBuffer, isErrFlag, config)); //请求失败
//                .doFinally(signalType -> doFinally(isErrFlag, aiRequest, dialogueId, contentStrBuffer, answerObj)); //请求完成后
        return sendHeartBeat(sessionId, queryId, null).concatWith(thirdPartyStream);
    }

    @Override
    public void addQuery(String queryContent) {
        User user = UserContext.getUser();
        String key = USER_SEARCH_PREFIX + user.getUserName();
        redissonUtils.zscoreAddAsync(key, getDoubleTime(), queryContent, null);
    }

    private double getDoubleTime() {
        return System.currentTimeMillis() / 1000.0;
    }

    @Override
    public Set<Object> getQueryHistory() {
        User user = UserContext.getUser();
        int MAX_COUNT = 100;
        return redissonUtils.getFixZSetMembers(USER_SEARCH_PREFIX + user.getUserName(), MAX_COUNT);
    }

    @Override
    public Boolean delQueryHistory(String queryContent) {
        User user = UserContext.getUser();
        String queryKey = USER_SEARCH_PREFIX + user.getUserName();
        if (StringUtils.isNotEmpty(queryContent)) {
            redissonUtils.removeZSetMemberAsync(queryKey, queryContent);
        } else {
            redissonUtils.removeAllZSetMembers(queryKey);
        }
        return true;
    }

    @Override
    public Flux<ReplyDTO> retrieveTecallTest(AiRequest aiRequest) {
        llmChatRequstTime = System.currentTimeMillis();
        //保存对话
        Long dialogueId = dialogueDomainService.addOrUpdateBySessionId(DialogueConvertor.INSTANCE.aiRequest2Dialogue(aiRequest));
        String sessionId = aiRequest.getSessionId();
        String queryId = aiRequest.getQueryId();

        // 检索召回+推理
        List<Document> documents = new ArrayList<>();
        List<Document> webRsDocuments = new ArrayList<>();

        //组装请求参数
        ExtendedConfig extendedConfig = buildExtendedConfig(aiRequest.getConfig(), aiRequest);
        //调用检索召回接口
        RetrievedData retrievedData = retrieveRecall(aiRequest, extendedConfig, dialogueId, Boolean.FALSE);
        if (Objects.nonNull(retrievedData)) {
            documents.addAll(retrievedData.getSimpleDocuments(storageProperties.getDefaultStorageProperties().getEndPoint()));
            List<Document> fullDocuments = retrievedData.getDocuments(storageProperties.getDefaultStorageProperties().getEndPoint());
            webRsDocuments.addAll(fullDocuments);
            extendedConfig.setDocuments(webRsDocuments, null);
            Long respTime = System.currentTimeMillis() - llmChatRequstTime;
            addQuestionAndAnswerRe(extendedConfig, dialogueId, aiRequest, "", JSON.toJSONString(webRsDocuments), AIResultTypeEnum.LLM.getCode(), respTime);
            if (!extendedConfig.enabledLlm()) {
                return ReplyDTO.fastReplyRe(sessionId, queryId, "", webRsDocuments, AIResultTypeEnum.LLM.getCode(), respTime);
            }
        }
        return modelBasedInferenceRe(JSON.toJSONString(webRsDocuments), aiRequest, extendedConfig, dialogueId, InputType.SEPARATE, null, new Config(), null, nacosConfig.getLlmOpenChatUrl(), AIResultTypeEnum.LLM.getCode(), null);
    }

    private ExtendedConfig buildExtendedConfig(String config, AiRequest aiRequest) {
        ExtendedConfig extendedConfig = new ExtendedConfig();
        JSONObject configJson = JSONObject.parseObject(config);
        configJson.put(MODEL_INFO, modelClient.getSimpByModeName(configJson.getString(MODEL_NAME)));
        configJson.put(RERANK_MODEL_INFO, modelClient.getSimpByModeName(configJson.getString(RERANK_MODEL_NAME)));
        configJson.put(QUERY, aiRequest.getContent());
        configJson.put(STREAM, true);
        configJson.put(NEED_TRACE_SOURCE, true);

        extendedConfig.init(JSON.toJSONString(configJson));
        extendedConfig.convertKBN2Array();
        return extendedConfig;
    }

//    @Override
//    public List<RerankModelDTO> getRerankModelInfos() {
//        return rerankModelConfig.getAllModel();
//    }


    @Override
    public RetrieveData retrieveDocuments(RetrieveDocReq4Platform req4Platform) {
        log.info("retrieveDocs4Plat接口请求参数:{}", JSON.toJSONString(req4Platform));
        if (req4Platform.getUseAuth()) {
            //查询当前用户对知识库是否有权限
            Set<String> authorizedKbNames = kbClient.searchList().stream().map(KnowledgeBaseDTO::getKbName).collect(Collectors.toSet());
            checkKbAuth(req4Platform.getKnowledge(), authorizedKbNames);
        }
        RetrieveDocReq retrieveDocReq = RetrieveDocReqConvertor.INSTANCE.RetrieveDocReq4Platform2RetrieveDocReq(req4Platform);
        if (Boolean.TRUE.equals(req4Platform.getRerankerEnabled())) {
            addModelUrl(req4Platform.getRerankerModel(), retrieveDocReq);
        }
        RetrieveData retrieveData = retrieveRecallByRetrieveDocReq(retrieveDocReq);
        if (retrieveData != null) {
            addConvertedFilePath(retrieveData.getDocumentsList());
        }
        return retrieveData;
    }

    /**
     * @param knowledgeBase     当前的知识库列表
     * @param authorizedKbNames 授权给该用户的列表
     */
    private void checkKbAuth(List<String> knowledgeBase, Set<String> authorizedKbNames) {
        Set<String> kbNames = new HashSet<>(knowledgeBase);
        authorizedKbNames.forEach(kbNames::remove);
        if (!CollectionUtils.isEmpty(kbNames)) {
            throw new ApplicationException(ErrCodeEnum.INSUFFICIENT_PERMISSIONS);
        }
    }

    private void addConvertedFilePath(List<RetrieveDoc> retrieveDocs) {
        List<Long> fileIds = retrieveDocs.stream().map(doc -> doc.getMetadata().getFileId()).toList();
        Map<Long, String> filePathMap = kbClient.getByIds(fileIds).stream().collect(Collectors.toMap(KnowledgeBaseFileDTO::getId, KnowledgeBaseFileDTO::getConvertedFilePath, (v1, v2) -> v1));
        retrieveDocs.forEach(doc -> {
            doc.setConvertedFilePath(filePathMap.get(doc.getMetadata().getFileId()));
            doc.setParsedFilePath(doc.getConvertedFilePath());
            doc.setPdfPages(PdfUtils.getPdfPages(doc.getConvertedFilePath()));
        });
    }

    private void addModelUrl(String modelName, RetrieveDocReq retrieveDocReq) {
        if (StringUtils.isNotBlank(modelName)) {
            ModelSimpDTO byModelName = modelClient.getSimpByModeName(modelName);
            retrieveDocReq.getRerankModelInfo().setUrl(byModelName.getUrl());
        }
    }


    private RetrieveData retrieveRecallByRetrieveDocReq(RetrieveDocReq retrieveDocReq) {
        LLMClientResp resp;
        try {
            log.info("retrieveRecall-检索召回请求参数:{}", JSON.toJSONString(retrieveDocReq));
            long startTime = System.currentTimeMillis();
//            resp = retrieveClient.retrievalDocuments(retrieveDocReq);
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<String> httpEntity = new HttpEntity<>(JSON.toJSONString(retrieveDocReq), headers);
            resp = restTemplate.postForObject(nacosConfig.getSearchDocsUrl(), httpEntity, LLMClientResp.class);
            log.info("knowledge---getBody:{}", JSON.toJSONString(resp));
            long endTime = System.currentTimeMillis();

            log.info("耗时：{} ms", endTime - startTime);
            if (Objects.nonNull(resp)) {
                if (resp.getCode().equals(200)) {
                    Object data = resp.getData();
                    return JSON.parseObject(JSON.toJSONString(data), RetrieveData.class);
                } else {
                    throw new ApplicationException(ErrCodeEnum.RETRIEVE_DOC_ERROR.getErrCode(), resp.getMsg());
                }
            }

        } catch (Exception e) {
            log.error("platform-retrieve-doc-error:", e);
        }
        return null;
    }


    @Override
    public DialogDTO questionRes(List<AiRequest> aiRequests) throws InterruptedException {
        if (CollectionUtils.isEmpty(aiRequests))
            return null;
        String appKey = UserContext.getUser().getAppKey();
        //创建对话
        AiRequest aiRequest = aiRequests.get(0);
        DialogCreateRequest dialogCreateRequest = new DialogCreateRequest();
        dialogCreateRequest.setLabel(aiRequest.getContent());
        dialogCreateRequest.setSessionId(aiRequest.getSessionId());
        dialogCreateRequest.setSysType(SysTypeEnums.INT_SESSION);
        dialogCreateRequest.setConfigId(aiRequest.getConfigId());
        dialogueAppService.create(dialogCreateRequest);

        //并发调用问答接口
        CountDownLatch countDownLatch = new CountDownLatch(aiRequests.size());
        aiRequests.forEach(item -> {
            executorService.execute(() -> {
                try {
                    HttpUtils.sendPostRequestForStream(appKey, "http://" + serverHostIp + ":" + serverPort + "/qa/ai/question_re", JSONObject.toJSONString(item));
                    countDownLatch.countDown();
                } catch (Exception e) {
                    log.error("并发调用问答口出现异常:请求参数:{},异常原因:{}", JSON.toJSONString(aiRequest), e);
                }
            });

        });
        //等待问答接口全部执行完成
        countDownLatch.await();
        //返回对话信息
        return dialogueAppService.getDialogBySessionId(aiRequest.getSessionId());
    }
}
