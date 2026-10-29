package com.gientech.ragindexservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.alibaba.excel.util.DateUtils;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.dto.FileChunkDTO;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import com.gientech.ragcommon.index.enmus.*;
import com.gientech.ragcommon.index.parameter.FileMultiversion;
import com.gientech.ragcommon.index.parameter.FileParseTaskInfo;
import com.gientech.ragcommon.index.parameter.ParseParam;
import com.gientech.ragcommon.infrastructure.emuns.RedisKeyEnums;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragindexservice.application.service.FileAppService;
import com.gientech.ragindexservice.application.service.ModelInfoAppService;
import com.gientech.ragindexservice.domain.entity.FileParseTask;
import com.gientech.ragindexservice.domain.entity.FolderInfo;
import com.gientech.ragindexservice.domain.entity.KnowledgeBase;
import com.gientech.ragindexservice.domain.entity.KnowledgeBaseList;
import com.gientech.ragindexservice.domain.service.*;
import com.gientech.ragindexservice.infrastructure.PdfConvertorUtils;
import com.gientech.ragindexservice.infrastructure.RemoteFileUtils;
import com.gientech.ragindexservice.infrastructure.RemoteGraphUtils;
import com.gientech.start.redisson.lock.RedissonLock;
import com.gientech.start.storage.properties.StorageProperties;
import com.gientech.start.storage.utils.FileStorageUtils;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;
import org.springframework.util.CollectionUtils;

import java.util.*;
import java.util.stream.Collectors;

import static com.gientech.ragcommon.index.constant.KbConfigConstant.EMBEDDING_MODEL_NAME;
import static com.gientech.ragcommon.index.enmus.FileFieldEnums.*;

@Slf4j
@Component
public class FileAppServiceImpl implements FileAppService {

    @Autowired
    private RemoteFileUtils remoteFileUtils;

    @Autowired
    private RemoteGraphUtils remoteGraphUtils;

    @Autowired
    private KnowledgeBaseListDomainService knowledgeBaseFileDomainService;

    @Autowired
    private SynLogDomainService synLogDomainService;

    @Autowired
    private KnowledgeBaseDomainService knowledgeBaseDomainService;

    @Autowired
    private StorageProperties storageProperties;

    @Autowired
    private FileStorageUtils fileStorageUtils;

    @Autowired
    private ChunnkDomainService chunnkDomainService;

    private JSONObject respJson = null;

    @Autowired
    private ModelInfoAppService modelInfoAppService;

    @Autowired
    private FolderInfoDomainService folderDomainService;

    @Autowired
    private PdfConvertorUtils pdfConvertorUtils;

    @Autowired
    private FileParseTaskDomainService fileParseTaskDomainService;

    @Autowired
    private RedissonLock redissonLock;

    @Override
    public void filesParse(FileParseTask task) {
        String filePath = null;
        Long kbId = null;
        Long taskId = null;
        FileParseTaskInfo.File file = null;
        Long fileId = null;
        try {
            FileParseTaskInfo param = JSONObject.parseObject(task.getTaskInfo(), FileParseTaskInfo.class);
            boolean needAuth = param.isNeedAuth();
            //设置用户上下文信息
            setUserContext(param.getUserId(), param.getUserName());
            kbId = param.getKnowledgeBaseId();
            taskId = task.getId();
            //文件解析
            param.setTaskId(taskId);
            file = param.getFiles().get(0);
            fileId = file.getFileId();
            String primitiveName = param.getPrimitiveName();
            param.setPrimitiveName(primitiveName);
            Boolean isExtract = param.getIsExtract();
            //解析中的文件
            KnowledgeBaseList knowledgeBaseFile = knowledgeBaseFileDomainService.findById(fileId);
            String objectName;
            if (StringUtils.isNotBlank(knowledgeBaseFile.getConvertedFilePath())) {
                // 重新解析时传原始路径
                objectName = knowledgeBaseFile.isNeedConvert2Md()
                        ? fileStorageUtils.getObjectNameFromUrl(knowledgeBaseFile.getFilePath())
                        : fileStorageUtils.getObjectNameFromUrl(knowledgeBaseFile.getConvertedFilePath());
            } else if (pdfConvertorUtils.isNeedConvert(knowledgeBaseFile)) {
                // 需要转换为 PDF
                objectName = pdfConvertorUtils.kbFile2Pdf(
                        knowledgeBaseFile, primitiveName, PlatFormEnums.RAG_QA.getCode(),
                        param.getUserId(), taskId
                );
            } else {
                // 不需要转换的文件，直接使用原路径
                if (knowledgeBaseFile.isConvertedFile() && !knowledgeBaseFile.isNeedConvert2Md()) {
                    knowledgeBaseFile.setConvertedFilePath(knowledgeBaseFile.getFilePath());
                    knowledgeBaseFile.setParsedFilePath(knowledgeBaseFile.getFilePath());
                }
                objectName = fileStorageUtils.getObjectNameFromUrl(knowledgeBaseFile.getFilePath());
            }
            //这个filePath是传给算法的
            filePath = String.join(FILE_SEPARATOR, storageProperties.getDefaultStorageProperties().getBucketName(), objectName);
            file.setFilePath(filePath);

            Integer parseType = knowledgeBaseFile.getParseType();
            file.setParseType(parseType);

            if (isExtract && ParseTypeEnums.FAQ_PARSE.getCode().equals(parseType)) {
                param.setKnowledgeBaseName(FAQ_EXTRACT_CHUNK_PREFIX + primitiveName);
                param.setIndexName(FAQ_EXTRACT_CHUNK_PREFIX + primitiveName);
            }

            if (
                    Objects.equals(knowledgeBaseFile.getStatus(), KbFileStatusEnums.RETRY.getValue()) ||
                            Objects.equals(knowledgeBaseFile.getStatus(), KbFileStatusEnums.PARSE_WAIT.getValue()) ||
                            Objects.equals(knowledgeBaseFile.getStatus(), KbFileStatusEnums.NORMAL.getValue()) ||
                            Objects.equals(knowledgeBaseFile.getStatus(), KbFileStatusEnums.PARSE_FAIL.getValue()) ||
                            Objects.equals(knowledgeBaseFile.getStatus(), KbFileStatusEnums.PARSE_SUCCESS.getValue())) {
                log.info("startTime:{}", DateUtils.format(new Date(), "yyyy-MM-dd HH:mm:ss"));
                //查询并设置模型
                setModel(param, needAuth);
                String parseResult = remoteFileUtils.fileParse(JSON.toJSONString(BeanUtil.copyProperties(param, ParseParam.class)));
                JSONObject jsonObject = JSON.parseObject(parseResult);
                Boolean isSuccess = jsonObject.getBoolean("success");
                if (isSuccess) {
                    knowledgeBaseFile.setStatus(KbFileStatusEnums.PARSE_ING.getValue());
                    // R14-C-FIX-32：start_time 的语义是"**开始解析**的时刻"，由派发前的 CAS 抢占写入。
                    // 原实现在解析**返回之后**才写，导致两件事：
                    //   ① 解析窗口内任务状态仍是 1/3，可被第二个执行者重复取到（重复解析）；
                    //   ② 超时计时从"解析结束"开始算，等于把超时窗口凭空延长一个解析时长。
                    // 这里只在确实没有值时兜底，绝不覆盖抢占时写入的真实起点。
                    if (Objects.isNull(task.getStartTime())) {
                        task.setStartTime(new Date());
                    }
                    task.setStatus(ParseTaskStatusEnums.DEAL_ING.getCode());
                } else {
                    knowledgeBaseFile.setStatus(KbFileStatusEnums.PARSE_FAIL.getValue());
                    synLogDomainService.saveLog(kbId, fileId, LogTypeEnums.FILE_PARSE.getCode(), null, parseResult);
                    task.setStatus(ParseTaskStatusEnums.DEAL_FAIL.getCode());
//                    fileParseTaskDomainService.updateStatusByIds(List.of(taskId),ParseTaskStatusEnums.DEAL_FAIL.getCode());
                }
                knowledgeBaseFile.setChunking(param.isNeedChunk());
                fileParseTaskDomainService.updateById(task);
                knowledgeBaseFileDomainService.update(knowledgeBaseFile);
                log.info("endTime:{}", DateUtils.format(new Date(), "yyyy-MM-dd HH:mm:ss"));
            }
        } catch (Exception e) {
            doException(kbId, fileId, taskId, file, filePath, e);
        }
    }

    @Override
    public void filesParseSync(FileParseTaskInfo param) {
        String filePath = null;
        Long kbId = null;
        Long taskId = null;
        FileParseTaskInfo.File file = null;
        Long fileId = null;
        try {
            kbId = param.getKnowledgeBaseId();
            //文件解析
            file = param.getFiles().get(0);
            fileId = file.getFileId();
            String primitiveName = param.getKnowledgeBaseName();
            param.setPrimitiveName(primitiveName);
            boolean saveTxt = param.isSaveTxt();
            boolean needChunk = param.isNeedChunk();
            //解析中的文件
            KnowledgeBaseList knowledgeBaseFile = knowledgeBaseFileDomainService.findById(fileId);
            String objectName;
            if (StringUtils.isNotBlank(knowledgeBaseFile.getConvertedFilePath())) {
                // 重新解析时传原始路径
                objectName = knowledgeBaseFile.isNeedConvert2Md()
                        ? fileStorageUtils.getObjectNameFromUrl(knowledgeBaseFile.getFilePath())
                        : fileStorageUtils.getObjectNameFromUrl(knowledgeBaseFile.getConvertedFilePath());
            } else if (pdfConvertorUtils.isNeedConvert(knowledgeBaseFile)) {
                // 需要转换为 PDF
                objectName = pdfConvertorUtils.kbFile2Pdf(
                        knowledgeBaseFile, primitiveName, PlatFormEnums.RAG_QA.getCode(),
                        param.getUserId(), null
                );
            } else {
                // 不需要转换的文件，直接使用原路径
                if (knowledgeBaseFile.isConvertedFile() && !knowledgeBaseFile.isNeedConvert2Md()) {
                    knowledgeBaseFile.setConvertedFilePath(knowledgeBaseFile.getFilePath());
                    knowledgeBaseFile.setParsedFilePath(knowledgeBaseFile.getFilePath());
                }
                objectName = fileStorageUtils.getObjectNameFromUrl(knowledgeBaseFile.getFilePath());
            }
            //这个filePath是传给算法的
            filePath = String.join(FILE_SEPARATOR, storageProperties.getDefaultStorageProperties().getBucketName(), objectName);
            file.setFilePath(filePath);

            Integer parseType = knowledgeBaseFile.getParseType();
            file.setParseType(parseType);

            if (
                    Objects.equals(knowledgeBaseFile.getStatus(), KbFileStatusEnums.PARSE_ING.getValue()) ||
                            Objects.equals(knowledgeBaseFile.getStatus(), KbFileStatusEnums.NORMAL.getValue()) ||
                            Objects.equals(knowledgeBaseFile.getStatus(), KbFileStatusEnums.PARSE_FAIL.getValue())
            ) {
                log.info("startTime:{}", DateUtils.format(new Date(), "yyyy-MM-dd HH:mm:ss"));
                doParse(param, needChunk, knowledgeBaseFile, saveTxt, filePath, file);
                log.info("endTime:{}", DateUtils.format(new Date(), "yyyy-MM-dd HH:mm:ss"));
            }
        } catch (Exception e) {
            doException(kbId, fileId, taskId, file, filePath, e);
        }
    }

    private void doException(Long kbId, Long fileId, Long taskId, FileParseTaskInfo.File file, String filePath, Exception e) {
        log.error("调用文档解析接口出现异常【" + filePath + "】,异常原因【" + e.getMessage() + "】", e);
        knowledgeBaseFileDomainService.updateStatusByIds(Lists.newArrayList(file.getFileId()), KbFileStatusEnums.PARSE_FAIL.getValue(), false);
        synLogDomainService.saveLog(kbId, fileId, LogTypeEnums.FILE_PARSE.getCode(), null, e.getMessage());
        if (!Objects.isNull(taskId))
            fileParseTaskDomainService.updateStatusByIds(List.of(taskId), ParseTaskStatusEnums.DEAL_FAIL.getCode());
        log.info("endTime:{}", DateUtils.format(new Date(), "yyyy-MM-dd HH:mm:ss"));
    }

    private void doParse(FileParseTaskInfo param,
                         Boolean needChunk,
                         KnowledgeBaseList knowledgeBaseFile,
                         Boolean saveTxt, String filePath,
                         FileParseTaskInfo.File file
    ) {
        Long fileId = file.getFileId();
        Long kbId = knowledgeBaseFile.getKbId();
        //查询并设置模型
        setModel(param);
        String parseResult = remoteFileUtils.fileSyncParse(JSON.toJSONString(BeanUtil.copyProperties(param, ParseParam.class)));
        JSONObject jsonObject = JSON.parseObject(parseResult);
        Boolean isSuccess = jsonObject.getBoolean("success");
        if (isSuccess) {
            if (needChunk) {
                JSONArray taskStatuses = jsonObject.getJSONArray("task_statuses");
                JSONObject taskStatus = (JSONObject) taskStatuses.get(0);
                //修订时间
                String reviseData = taskStatus.getString("revise_date");
                knowledgeBaseFile.setReviseDate(reviseData);
                knowledgeBaseFile.setChunking(true);
            }
            knowledgeBaseFile.setStatus(KbFileStatusEnums.PARSE_SUCCESS.getValue());
            if (saveTxt) {
                knowledgeBaseFile.setFullTextPath(getFullTextPath(filePath));
            }
            knowledgeBaseFile.setChunkType(param.getFileType());
            knowledgeBaseFileDomainService.update(knowledgeBaseFile);
        } else {
            log.error("文档解析失败【" + filePath + "】");
            knowledgeBaseFileDomainService.updateStatusByIds(Lists.newArrayList(file.getFileId()), KbFileStatusEnums.PARSE_FAIL.getValue(), false);
            //记录失败日志
            synLogDomainService.saveLog(kbId, fileId, LogTypeEnums.FILE_PARSE.getCode(), jsonObject, null);
        }
    }

    private void setUserContext(String userId, String userName) {
        //设置用户上下文信息
        User user = new User();
        user.setUserId(userId);
        user.setUserName(userName);
        UserContext.setUser(user);
    }

    private void setModel(FileParseTaskInfo param) {
        String embeddingModelName = param.getEmbeddingModelName();
        String modelName = param.getModelName();
        String multiModelName = param.getMultiModelName();
        ModelSimpDTO embeddingModel = modelInfoAppService.getSimpByModeName(embeddingModelName);
        ModelSimpDTO model = modelInfoAppService.getSimpByModeName(modelName);
        ModelSimpDTO multiModel = modelInfoAppService.getSimpByModeName(multiModelName);
        param.setModelInfo(model);
        param.setEmbeddingNodelInfo(embeddingModel);
        param.setMultiModelInfo(multiModel);
    }

    private void setModel(FileParseTaskInfo param, boolean needAuth) {
        //String embeddingModelName = param.getEmbeddingModelName();
        KnowledgeBase kb = knowledgeBaseDomainService.findByKbId(param.getKnowledgeBaseId());
        JSONObject confJson = JSON.parseObject(kb.getConfig());
        String embeddingModelName = confJson.getString(EMBEDDING_MODEL_NAME);
        String modelName = param.getModelName();
        String multiModelName = param.getMultiModelName();
        ModelSimpDTO embeddingModel = modelInfoAppService.getSimpByModeName(embeddingModelName, needAuth);
        ModelSimpDTO model = modelInfoAppService.getSimpByModeName(modelName, needAuth);
        ModelSimpDTO multiModel = modelInfoAppService.getSimpByModeName(multiModelName, needAuth);
        param.setModelInfo(model);
        param.setEmbeddingNodelInfo(embeddingModel);
        param.setMultiModelInfo(multiModel);
    }

    private String getFullTextPath(String filePath) {
        int lastIndexOfSlash = filePath.lastIndexOf("/");
        StringBuilder fullTextPath = new StringBuilder(filePath.substring(0, lastIndexOfSlash));
        String fileName = filePath.substring(lastIndexOfSlash + 1);
        fullTextPath.append("/").append("parsed").append("/").append(fileName).append(".txt");
        return fullTextPath.toString();

    }

    @Async("asyncExecutor")
    @Override
    public void faqExtract(FileParseTaskInfo param) {
        if (CollectionUtils.isEmpty(param.getFiles())) {
            return;
        }
        FileParseTaskInfo.File file = param.getFiles().get(0);
        String kbName = param.getKnowledgeBaseName();

        Long fileId = file.getFileId();
        KnowledgeBaseList knowledgeBaseFile = knowledgeBaseFileDomainService.findById(fileId);
        Integer parseType = knowledgeBaseFile.getParseType();

        //判断是否解析失败，解析失败直接退出
        Integer status = knowledgeBaseFile.getStatus();
        if (KbFileStatusEnums.PARSE_FAIL.getValue().equals(status)) {
            knowledgeBaseFile.setFaqExtractStatus(FaqExtractStatusEnums.EXTRACT_FAIL.getValue());
            knowledgeBaseFileDomainService.update(knowledgeBaseFile);
            return;
        }

        //创建FAQ管理的数据
        KnowledgeBaseList faqFile = createFaqFile(knowledgeBaseFile, kbName);
        Long faqFileId = faqFile.getId();

        //FAQ抽取
        if (!FaqExtractStatusEnums.EXTRACT_SUCCESS.getValue().equals(knowledgeBaseFile.getFaqExtractStatus())) {
            String primitiveName = param.getPrimitiveName();
            Integer fileFaqMaxNums = Objects.isNull(param.getFileFaqMaxNums()) ? 0 : param.getFileFaqMaxNums();
            try {
                //获取文件的chunk
                String tableName = kbName;
                if (ParseTypeEnums.FAQ_PARSE.getCode().equals(parseType)) {
                    tableName = FAQ_EXTRACT_CHUNK_PREFIX + kbName;
                }
                List<FileChunkDTO> chunks = getAndRemoveFileChunks(tableName, fileId, parseType, null, null);
                // R13-FIX-FAQ-05：无 chunk 时原实现继续调用模型并标记成功（0 产出也算成功）。
                if (chunks.isEmpty()) {
                    throw new ApplicationException(ErrCodeEnum.DOC_CHUNK_ERROR);
                }
                JSONObject faqReq = new JSONObject();
                JSONArray documentList = new JSONArray();
                chunks.forEach(chunk -> {
                    JSONObject document = new JSONObject();
                    document.put("page_content", chunk.getContent());
                    JSONObject metadata = new JSONObject();
                    metadata.put("source", knowledgeBaseFile.getFilePath());
                    //FAQ抽取的文件id
                    metadata.put("document_id", knowledgeBaseFile.getId().toString());
                    //FAQ管理中的文件id
                    metadata.put("file_id", faqFileId.toString());
                    metadata.put("folder_id", faqFileId.toString());
                    metadata.put("knowledge_base_name", primitiveName);
                    document.put("metadata", metadata);
                    documentList.add(document);
                });
                faqReq.put("model_info", modelInfoAppService.getSimpByModeName(param.getFaqModelName()));
                faqReq.put("top_k", fileFaqMaxNums);
                faqReq.put("document_list", documentList);
                log.warn("文本chunk FAQ抽取开始，params:" + faqReq.toJSONString());
                String resp = remoteFileUtils.faqExtract(JSONObject.toJSONString(faqReq));
                respJson = JSONObject.parseObject(resp);
                if (!Objects.equals(respJson.getInteger("code"), 200))
                    throw new ApplicationException(ErrCodeEnum.FAQ_EXTRACT_ERROR);
                //更新数据库表状态extract status
                knowledgeBaseFile.setFaqExtractStatus(FaqExtractStatusEnums.EXTRACT_SUCCESS.getValue());
                knowledgeBaseFileDomainService.update(knowledgeBaseFile);

                //FAQ管理中未查到数据，持久化FAQ管理中创建临时文件,并创建对应的文件件
                persistenceFileAndCreateFolder(faqFile, knowledgeBaseFile);

            } catch (Exception e) {
                log.error("文档抽取失败【" + file.getFilePath() + "】,异常原因【" + e.getMessage() + "】");
                //更新数据库表状态extract status
                knowledgeBaseFile.setFaqExtractStatus(FaqExtractStatusEnums.EXTRACT_FAIL.getValue());
                knowledgeBaseFileDomainService.update(knowledgeBaseFile);
                synLogDomainService.saveLog(knowledgeBaseFile.getKbId(), fileId, LogTypeEnums.FAQ_EXTRACT.getCode(), respJson, e.getMessage());
            }
        }
    }

    private KnowledgeBaseList createFaqFile(KnowledgeBaseList knowledgeBaseFile, String primitiveName) {
        Long fileId = knowledgeBaseFile.getId();
        String filePath = knowledgeBaseFile.getFilePath();
        List<KnowledgeBaseList> faqFiles = knowledgeBaseFileDomainService.findFileByFilePaths(knowledgeBaseFile.getKbId(), Arrays.asList(filePath), ParseTypeEnums.FAQ_MANAGEMENT.getCode());
        KnowledgeBaseList faqFile = CollectionUtils.isEmpty(faqFiles) ? null : faqFiles.get(0);

        if (!Objects.isNull(faqFile)) {
            //如果有文件夹
            if (!Objects.isNull(faqFile.getFolderId()) && !Objects.isNull(knowledgeBaseFile.getFolderId())) {
                FolderInfo faqFolder = folderDomainService.findById(faqFile.getFolderId());
                FolderInfo sourceFolder = folderDomainService.findById(knowledgeBaseFile.getFolderId());
                if (!Objects.isNull(faqFolder) && !Objects.isNull(sourceFolder)
                        && !Objects.isNull(faqFolder.getFullPath()) && !Objects.isNull(sourceFolder.getFullPath())
                        && StringUtils.equals(faqFolder.getFullPath(), sourceFolder.getFullPath())) {
                    //删除faq管理中的faq数据
                    chunnkDomainService.deleteFaq(primitiveName, Arrays.asList(fileId), Arrays.asList(faqFile.getId()));
                }
            } else if (Objects.isNull(faqFile.getFolderId()) && Objects.isNull(knowledgeBaseFile.getFolderId())) {
                //删除faq管理中的faq数据
                chunnkDomainService.deleteFaq(primitiveName, Arrays.asList(fileId), Arrays.asList(faqFile.getId()));
            } else {
                faqFile = createTempFile(knowledgeBaseFile);
            }
        } else {
            faqFile = createTempFile(knowledgeBaseFile);
        }
        return faqFile;
    }

    private void persistenceFileAndCreateFolder(KnowledgeBaseList tempFile, KnowledgeBaseList knowledgeBaseFile) {
        Long kbId = tempFile.getKbId();
        tempFile.setTempStatus(TempStatusEnums.PERSISTENCE.getCode());
//        tempFile.setSourceId(knowledgeBaseFile.getId());
        Long folderId = knowledgeBaseFile.getFolderId();
        if (!Objects.isNull(folderId)) {
            FolderInfo folder = folderDomainService.findById(folderId);
            String fullPath = folder.getFullPath();
            Long fileFolderId = folderDomainService.createFolderByFullPath(kbId, fullPath, FolderTypeEnums.FAQ_MANAGEMENT.getCode());
            tempFile.setFolderId(fileFolderId);
        }
        knowledgeBaseFileDomainService.update(tempFile);
    }

    private KnowledgeBaseList createTempFile(KnowledgeBaseList knowledgeBaseFile) {
        KnowledgeBaseList tempFile = BeanUtil.copyProperties(knowledgeBaseFile, KnowledgeBaseList.class, "id", "folderId");
        tempFile.setStatus(KbFileStatusEnums.PARSE_SUCCESS.getValue());
        tempFile.setTempStatus(TempStatusEnums.TEMP.getCode());
        tempFile.setFaqExtractStatus(FaqExtractStatusEnums.EXTRACT_SUCCESS.getValue());
        tempFile.setParseType(ParseTypeEnums.FAQ_MANAGEMENT.getCode());
        List<KnowledgeBaseList> tempFiles = knowledgeBaseFileDomainService.insertBatch(Arrays.asList(tempFile));
        tempFile = tempFiles.get(0);
        return tempFile;

    }

    public List<FileChunkDTO> getAndRemoveFileChunks(String tableName, Long docId, Integer parseType, Integer pageNo, Integer pageSize) {
        KnowledgeBaseList knowledgeBaseFile = knowledgeBaseFileDomainService.findById(docId);
        if (Objects.isNull(knowledgeBaseFile)) throw new ApplicationException(ErrCodeEnum.KB_FILE_NOT_EXISTS_ERROR);
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(knowledgeBaseFile.getKbId());
        if (Objects.isNull(knowledgeBase)) throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        String fileName = knowledgeBaseFile.getFileName();
        JSONObject query = new JSONObject();
        query.put("index_name", Arrays.asList(tableName, TABLE_CHUNKS_PREFIX + tableName));
        query.put("sort_field", "create_time");
        query.put("sort_mode", "asc");
        if (Objects.nonNull(pageNo) && Objects.nonNull(pageSize) && pageNo > 0 && pageSize > 0) {
            query.put("page_no", pageNo);
            query.put("page_num", pageSize);
        }

        List<JSONObject> searchCondtions = new ArrayList<>();
        JSONObject condtion = new JSONObject();
        String fileType = fileName.substring(fileName.lastIndexOf(".") + 1);
        if (!FileFieldEnums.FILE_TYPE_LIST.contains(fileType)) {
            String fileNamePrefix = fileName.substring(0, fileName.lastIndexOf("."));
            fileName = fileNamePrefix + ".pdf";
        }
        condtion.put("title", Arrays.asList(fileName));
        searchCondtions.add(condtion);
        query.put("condition_json", searchCondtions);

        // R13-FIX-FAQ-04：非 FILE_TYPE_LIST(xlsx/xls/csv) 的扩展名会被改写成 .pdf 去匹配
        // ES 的 metadata.title，而实际 title 是原名（如 docx-plain.docx）→ 查不到 chunk，
        // 上游仍把 FAQ 标记成功（"假成功，0 产出"）。这里先按改写名查，查不到再用原名兜底。
        String resp = remoteFileUtils.pageListEs(JSONObject.toJSONString(query));
        respJson = JSONObject.parseObject(resp);
        if (!Objects.equals(respJson.getInteger("code"), 200))
            throw new ApplicationException(ErrCodeEnum.DOC_CHUNK_ERROR);
        JSONObject data = respJson.getJSONObject("data");
        List<FileChunkDTO> chunks = Lists.newArrayList();
        JSONArray resultData = data == null ? null : data.getJSONArray("result_data");
        if (resultData == null || resultData.isEmpty()) {
            String originalName = knowledgeBaseFile.getFileName();
            if (!originalName.equals(fileName)) {
                JSONObject retryQuery = JSONObject.parseObject(JSONObject.toJSONString(query));
                List<JSONObject> retryConds = new ArrayList<>();
                JSONObject retryCond = new JSONObject();
                retryCond.put("title", Arrays.asList(originalName));
                retryConds.add(retryCond);
                retryQuery.put("condition_json", retryConds);
                String retryResp = remoteFileUtils.pageListEs(JSONObject.toJSONString(retryQuery));
                JSONObject retryJson = JSONObject.parseObject(retryResp);
                if (retryJson != null && Objects.equals(retryJson.getInteger("code"), 200)) {
                    JSONObject retryData = retryJson.getJSONObject("data");
                    if (retryData != null) {
                        resultData = retryData.getJSONArray("result_data");
                        log.warn("chunk 查询按改写名未命中，已按原始文件名{}重试，命中{}条", originalName,
                                resultData == null ? 0 : resultData.size());
                    }
                }
            }
        }
        if (resultData == null || resultData.isEmpty()) {
            log.warn("文件{}在索引中没有任何 chunk（索引名={}），返回空列表由调用方判定失败", fileName, tableName);
            return chunks;
        }
        resultData.forEach(result -> {
            JSONObject dataJson = ((JSONObject) result).getJSONObject("_source");
            String chunkContent = dataJson.getString("page_content");
            JSONObject chunkMetadataJson = dataJson.getJSONObject("metadata");
            FileChunkDTO fileChunkDTO = new FileChunkDTO();
            fileChunkDTO.setPageNumbers(chunkMetadataJson.getJSONArray("page_number"));
            fileChunkDTO.setPositions(chunkMetadataJson.getJSONArray("position"));
            fileChunkDTO.setPageSizes(chunkMetadataJson.getJSONArray("page_size"));
            fileChunkDTO.setOffsets(chunkMetadataJson.getJSONArray("offset"));
            fileChunkDTO.setType(chunkMetadataJson.getString("type"));
            if (org.apache.commons.lang3.StringUtils.isNotBlank(chunkContent)) {
                fileChunkDTO.setContent(chunkContent);
            }
            chunks.add(fileChunkDTO);
        });

        if (ParseTypeEnums.FAQ_PARSE.getCode().equals(parseType)) {
            //删除文本块
            chunnkDomainService.deleteTable(tableName);
            //删除table_chunks_
            chunnkDomainService.deleteTable(TABLE_CHUNKS_PREFIX + tableName);
            //删除table_summary_
            chunnkDomainService.deleteTable(FileFieldEnums.TABLE_SUMMARY_PREFIX + tableName);
        }
        return chunks;
    }

    @Async("asyncExecutor")
    @Override
    public void generateGraph(FileParseTaskInfo param) {
        FileParseTaskInfo.File file = param.getFiles().get(0);
        Long fileId = file.getFileId();
        Long kbId = param.getKnowledgeBaseId();
        KnowledgeBaseList knowledgeBaseFile = knowledgeBaseFileDomainService.findById(file.getFileId());
        if (Objects.isNull(knowledgeBaseFile)) throw new ApplicationException(ErrCodeEnum.KB_FILE_NOT_EXISTS_ERROR);
        String filePath = knowledgeBaseFile.getConvertedFilePath();
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase)) throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        try {
            ModelSimpDTO modelInfo = modelInfoAppService.getSimpByModeName(param.getGenerateGraphModelName());
            if (!Objects.isNull(modelInfo) && StringUtils.isEmpty(modelInfo.getApiKey()))
                modelInfo.setApiKey("");
            // R14-LIVE-14：这里必须用**原始名**（kb_9），不能用中文展示名。
            // Python 侧 graph_fun_tool.get_document_chunk 直接拿 space_name 当 ES 索引名：
            //   index_name = [space_name, "table_chunks_" + space_name]
            // 传 "R12验收主链" 时索引不存在 → es 查询报 'NoneType' object is not subscriptable
            // → 上层只看到"该知识库未查询到相关文本"，任务被置为解析失败(4)。
            // 实测：kb_9 的 10 个文件 graph_parse_status 全是 1(未做) 或 4(失败)，从来没有 3(成功)。
            // Nebula 空间名也一并按原始名拼（g_kb_9），与磁盘上已有的图保持一致。
            String spaceName = knowledgeBase.getPrimitiveName();
            if (StringUtils.isBlank(spaceName)) {
                spaceName = param.getKnowledgeBaseName();
            }
            JSONObject graphReq = new JSONObject();
            graphReq.put("space_name", spaceName);
            graphReq.put("embedding_model_name", param.getEmbeddingModelName());
            graphReq.put("model_info", modelInfo);
            graphReq.put("col_name", "title");
            // R13-FIX-GRAPH-08：原实现取 convertedFilePath 的文件名（如 xxx.xlsx.md）去匹配 ES 的
            // metadata.title（原始文件名 xxx.xlsx），一定匹配不到 -> 图抽取报"未查询到相关文本"。
            // 这里优先用文件表里的原始文件名，取不到时再退回 converted 名并剥掉 .md 后缀。
            String matchTitle = knowledgeBaseFile.getFileName();
            if (StringUtils.isBlank(matchTitle)) {
                matchTitle = filePath.substring(filePath.lastIndexOf("/") + 1);
                if (matchTitle.endsWith(".md")) {
                    matchTitle = matchTitle.substring(0, matchTitle.length() - 3);
                }
            }
            graphReq.put("col_values", Arrays.asList(matchTitle));
            String graphPrompt = knowledgeBase.getGraphPrompt();
            if (StringUtils.isNotBlank(graphPrompt))
                graphReq.put("entity_types", Arrays.asList(graphPrompt.split(",")));
            log.warn("生成图数据请求参数,params:{}", JSONObject.toJSONString(graphReq));
            String resp = remoteGraphUtils.generateGraph(JSONObject.toJSONString(graphReq));
            respJson = JSONObject.parseObject(resp);
            if (!Objects.equals(respJson.getInteger("code"), 200))
                throw new ApplicationException(ErrCodeEnum.GRAPH_PARSE_ERROR);
            // R15 W06 / A06：零产出不得记成功。
            // 实测 file 343 曾 gps=3（成功）但图里 0 条边——写边全失败却没校验，
            // 结果"解析成功"的文件在问答里永远召不回。这里用算法侧回传的写入统计设闸门。
            JSONObject graphData = respJson.getJSONObject("data");
            int edgesTotal = graphData == null ? 0 : graphData.getIntValue("edges_total");
            int edgesWritten = graphData == null ? 0 : graphData.getIntValue("edges_written");
            if (edgesTotal <= 0 || edgesWritten <= 0) {
                log.error("图解析零产出，判失败：fileId={} triples_total={} edges_total={} edges_written={}",
                        fileId,
                        graphData == null ? -1 : graphData.getIntValue("triples_total"),
                        edgesTotal, edgesWritten);
                throw new ApplicationException(ErrCodeEnum.GRAPH_PARSE_ERROR);
            }
            //修改数据库图解析状态为成功
            knowledgeBaseFile.setGraphParseStatus(GraphParseStatusEnums.PARSE_SUCCESS.getValue());
            knowledgeBaseFileDomainService.update(knowledgeBaseFile);
        } catch (Exception e) {
            log.error("图生成失败【" + file.getFilePath() + "】,异常原因【" + e.getMessage() + "】");
            //更新数据库表状态extract status
            knowledgeBaseFile.setGraphParseStatus(GraphParseStatusEnums.PARSE_FAIL.getValue());
            knowledgeBaseFileDomainService.update(knowledgeBaseFile);
            synLogDomainService.saveLog(knowledgeBaseFile.getKbId(), fileId, LogTypeEnums.FILE_GRAPH.getCode(), respJson, e.getMessage());
        }
    }

    @Override
    public void fileMultiversionParse(Long kbId, List<Long> fileIds, MultiversionParseEnums multiversionParseEnums, List<Integer> parseTypes, boolean needAuth) {
//        String lockName = RedisKeyEnums.FILE_MULTI_VERSION_PREFIX + kbId;
        try {
//            redissonLock.lock(lockName);
            KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
            String modelName = knowledgeBase.getModelName();
            ModelSimpDTO modelInfo = modelInfoAppService.getSimpByModeName(modelName, needAuth);
            //需要多版本解析的文件
            List<KnowledgeBaseList> needMultiVersionFiles = knowledgeBaseFileDomainService.findByIds(fileIds);
            //所有的文件
            List<KnowledgeBaseList> allFiles = knowledgeBaseFileDomainService.findFileByKbId(kbId, parseTypes);

            Map<String, KnowledgeBaseList> needMultiVersionMap = Maps.newHashMap();
            List<FileMultiversion> needMultiVersion = Lists.newArrayList();
            needMultiVersionFiles.stream().forEach(knowledgeBaseList -> {
                needMultiVersionMap.put(knowledgeBaseList.getFileName(), knowledgeBaseList);
//                String groupId = knowledgeBaseList.getGroupId();
                FileMultiversion fileMultiversion = new FileMultiversion();
                fileMultiversion.setName(knowledgeBaseList.getFileName());
                fileMultiversion.setId(String.valueOf(knowledgeBaseList.getId()));
                fileMultiversion.setGroupId("");
                needMultiVersion.add(fileMultiversion);
//                if (StringUtils.isEmpty(groupId) || Objects.isNull(knowledgeBaseFileDomainService.findFileGroup(kbId, groupId, parseTypes))) {
//                    fileMultiversion.setName(knowledgeBaseList.getFileName());
//                    fileMultiversion.setId(String.valueOf(knowledgeBaseList.getId()));
//                    fileMultiversion.setGroupId("");
//                    needMultiVersion.add(fileMultiversion);
//                }
            });

            //如果没有需要版本识别的文件,不处理
            if (CollectionUtils.isEmpty(needMultiVersion))
                return;

            List<FileMultiversion> haveVersion = Lists.newArrayList();
            allFiles.forEach(knowledgeBaseList -> {
                if (Objects.isNull(needMultiVersionMap.get(knowledgeBaseList.getFileName()))) {
                    FileMultiversion fileMultiversion = new FileMultiversion();
                    fileMultiversion.setName(knowledgeBaseList.getFileName());
                    fileMultiversion.setId(String.valueOf(knowledgeBaseList.getId()));
                    fileMultiversion.setGroupId(StringUtils.isNotBlank(knowledgeBaseList.getGroupId()) ? knowledgeBaseList.getGroupId() : "");
                    haveVersion.add(fileMultiversion);
                }
            });

            String primitiveName = knowledgeBase.getPrimitiveName();
            JSONObject reqParam = new JSONObject();
            reqParam.put("knowledge_base_name", primitiveName);
            reqParam.put("need_version_doc", needMultiVersion);
            reqParam.put("have_version_doc", haveVersion);
            reqParam.put("model_info", modelInfo);
            reqParam.put("status", multiversionParseEnums.getCode());
            String result = remoteFileUtils.fileMultiVersion(JSONObject.toJSONString(reqParam));
            JSONObject resultJson = JSONObject.parseObject(result);
            if (!resultJson.getBoolean("success"))
                throw new ApplicationException(ErrCodeEnum.FILE_MULTI_VERSION_PARSE_ERROR);
            List<FileMultiversion> fileInfos = resultJson.getList("data", FileMultiversion.class);
            //处理文件多版本结果
            doFileMultiversion(kbId, knowledgeBase.getPrimitiveName(), fileInfos);
        } catch (Exception e) {
            log.error("执行文件多版本接口出现异常,{}", e.getMessage());
        }
//        finally {
//            log.error("释放锁成功:" + JSON.toJSONString(fileIds));
//            redissonLock.unlock(lockName);
//        }
    }

    @Override
    public void fileMultiversionParse(Long kbId, List<Long> fileIds, MultiversionParseEnums multiversionParseEnums, List<Integer> parseTypes) {
//        String lockName = RedisKeyEnums.FILE_MULTI_VERSION_PREFIX + kbId;
        try {
//            redissonLock.lock(lockName);
            KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
            String modelName = knowledgeBase.getModelName();
            ModelSimpDTO modelInfo = modelInfoAppService.getSimpByModeName(modelName);
            //需要多版本解析的文件
            List<KnowledgeBaseList> needMultiVersionFiles = knowledgeBaseFileDomainService.findByIds(fileIds);
            //所有的文件
            List<KnowledgeBaseList> allFiles = knowledgeBaseFileDomainService.findFileByKbId(kbId, parseTypes);

            Map<String, KnowledgeBaseList> needMultiVersionMap = Maps.newHashMap();
            List<FileMultiversion> needMultiVersion = Lists.newArrayList();
            needMultiVersionFiles.stream().forEach(knowledgeBaseList -> {
                needMultiVersionMap.put(knowledgeBaseList.getFileName(), knowledgeBaseList);
//                String groupId = knowledgeBaseList.getGroupId();
                FileMultiversion fileMultiversion = new FileMultiversion();
                fileMultiversion.setName(knowledgeBaseList.getFileName());
                fileMultiversion.setId(String.valueOf(knowledgeBaseList.getId()));
                fileMultiversion.setGroupId("");
                needMultiVersion.add(fileMultiversion);
//                if (StringUtils.isEmpty(groupId) || Objects.isNull(knowledgeBaseFileDomainService.findFileGroup(kbId, groupId, parseTypes))) {
//                    fileMultiversion.setName(knowledgeBaseList.getFileName());
//                    fileMultiversion.setId(String.valueOf(knowledgeBaseList.getId()));
//                    fileMultiversion.setGroupId("");
//                    needMultiVersion.add(fileMultiversion);
//                }
            });

            //如果没有需要版本识别的文件,不处理
            if (CollectionUtils.isEmpty(needMultiVersion))
                return;

            List<FileMultiversion> haveVersion = Lists.newArrayList();
            allFiles.forEach(knowledgeBaseList -> {
                if (Objects.isNull(needMultiVersionMap.get(knowledgeBaseList.getFileName()))) {
                    FileMultiversion fileMultiversion = new FileMultiversion();
                    fileMultiversion.setName(knowledgeBaseList.getFileName());
                    fileMultiversion.setId(String.valueOf(knowledgeBaseList.getId()));
                    fileMultiversion.setGroupId(StringUtils.isNotBlank(knowledgeBaseList.getGroupId()) ? knowledgeBaseList.getGroupId() : "");
                    haveVersion.add(fileMultiversion);
                }
            });

            String primitiveName = knowledgeBase.getPrimitiveName();
            JSONObject reqParam = new JSONObject();
            reqParam.put("knowledge_base_name", primitiveName);
            reqParam.put("index_name", primitiveName);
            reqParam.put("need_version_doc", needMultiVersion);
            reqParam.put("have_version_doc", haveVersion);
            reqParam.put("model_info", modelInfo);
            reqParam.put("status", multiversionParseEnums.getCode());
            String result = remoteFileUtils.fileMultiVersion(JSONObject.toJSONString(reqParam));
            JSONObject resultJson = JSONObject.parseObject(result);
            if (!resultJson.getBoolean("success"))
                throw new ApplicationException(ErrCodeEnum.FILE_MULTI_VERSION_PARSE_ERROR);
            List<FileMultiversion> fileInfos = resultJson.getList("data", FileMultiversion.class);
            //处理文件多版本结果
            doFileMultiversion(kbId, knowledgeBase.getPrimitiveName(), fileInfos);
        } catch (Exception e) {
            log.error("执行文件多版本接口出现异常,{}", e.getMessage());
        }
//        finally {
//            log.error("释放锁成功:" + JSON.toJSONString(fileIds));
//            redissonLock.unlock(lockName);
//        }
    }

    private void doFileMultiversion(Long kbId, String primitiveName, List<FileMultiversion> fileInfos) {
        if (!CollectionUtils.isEmpty(fileInfos)) {
            Map<String, List<FileMultiversion>> fileMap = fileInfos.stream().collect(Collectors.groupingBy(FileMultiversion::getGroupId));
            fileMap.forEach((groupId, files) -> {
                if (StringUtils.isNotBlank(groupId)) {
                    FileMultiversion fileMultiversion = files.get(0);
                    String fileName = fileMultiversion.getName();
                    String parentFileName = fileName;
                    String versionDate = fileMultiversion.getVersionDate();
                    KnowledgeBaseList dbFile = knowledgeBaseFileDomainService.findByKbIdAndGroupIds(kbId, groupId);
                    if (!Objects.isNull(dbFile))
                        parentFileName = dbFile.getParentFileName();
                    // R14-C-FIX-01（F04 文档稳定身份）：算法端 FILENAME_CONTENT 归并会在"样本 chunk 数不足"时
                    // 用 1 个 chunk 的相似占比（1/1=1.0 >= 阈值）把不同文档并入同一 group。实测
                    // R12FIX-credit-ledger.xlsx 被并入 R12FIX-product-loan.docx 组（parent/group 双双被改写），
                    // 后果是检索按 parent_file_name 做版本去重时把台账当"旧版本"挤掉、引用指错文件。
                    // 此处做写入前校验：只有"归一键"（去扩展名后去掉末尾 (n)/（n） 版本标记）与组父名一致的文件
                    // 才允许进组；不一致的一律跳过并告警，绝不改写其 parent_file_name/group_id。
                    List<Long> ids = Lists.newArrayList();
                    List<FileMultiversion> rejectedFiles = Lists.newArrayList();
                    String parentKey = versionKeyOf(parentFileName);
                    for (FileMultiversion f : files) {
                        String fileKey = versionKeyOf(f.getName());
                        boolean parseable = true;
                        long parsedId = -1L;
                        try {
                            parsedId = Long.parseLong(f.getId());
                        } catch (NumberFormatException nfe) {
                            parseable = false;
                        }
                        if (parseable && parentKey.equals(fileKey)) {
                            ids.add(parsedId);
                        } else {
                            rejectedFiles.add(f);
                        }
                    }
                    // R14-C-FIX-16（TL 裁决 B）：group 变更审计。只记录、不参与业务判定。
                    // 目的：下次再出现"不同文档被并进同一版本组"时，能直接查到 fileId、旧/新 group 与父名、
                    // 触发路径与时间，而不是像本轮那样只能靠日志时间窗反推。
                    auditGroupChange(kbId, groupId, parentFileName, versionDate, ids, rejectedFiles);
                    if (!rejectedFiles.isEmpty()) {
                        log.warn("R14-C-FIX-01 拒绝跨文档归组 kbId={} groupId={} parentFile={} parentKey={} rejected={}",
                                kbId, groupId, parentFileName, parentKey, describeFiles(rejectedFiles));
                    }
                    if (ids.isEmpty())
                        return;
                    knowledgeBaseFileDomainService.updateMultiversion(ids, parentFileName, groupId, versionDate);
                    //更新es和milvus中的versiondate
                    updateVersion(primitiveName, ids, versionDate);
                }
            });
        }
    }

    /** R14-C-FIX-16：把 group 变更前后值打成一行可 grep 的审计日志（不参与判定）。 */
    private void auditGroupChange(Long kbId, String groupId, String parentFileName, String versionDate,
                                  List<Long> acceptedIds, List<FileMultiversion> rejectedFiles) {
        try {
            List<Long> probe = Lists.newArrayList(acceptedIds);
            for (FileMultiversion f : rejectedFiles) {
                try {
                    probe.add(Long.parseLong(f.getId()));
                } catch (NumberFormatException ignore) {
                    // id 非数字：无法反查旧值，审计里保留原始 id 字符串
                }
            }
            Map<Long, KnowledgeBaseList> before = new HashMap<>();
            if (!probe.isEmpty()) {
                List<KnowledgeBaseList> rows = knowledgeBaseFileDomainService.findByIds(probe);
                if (rows != null) {
                    for (KnowledgeBaseList r : rows) {
                        if (r != null && r.getId() != null) {
                            before.put(r.getId(), r);
                        }
                    }
                }
            }
            for (Long id : acceptedIds) {
                KnowledgeBaseList old = before.get(id);
                log.info("[AUDIT-GROUP] action=JOIN trigger=file_parse_callback kbId={} fileId={} oldGroupId={} oldParent={} newGroupId={} newParent={} versionDate={}",
                        kbId, id,
                        old == null ? null : old.getGroupId(),
                        old == null ? null : old.getParentFileName(),
                        groupId, parentFileName, versionDate);
            }
            for (FileMultiversion f : rejectedFiles) {
                KnowledgeBaseList old = null;
                try {
                    old = before.get(Long.parseLong(f.getId()));
                } catch (NumberFormatException ignore) {
                    // 保持 old=null
                }
                log.warn("[AUDIT-GROUP] action=REJECT trigger=file_parse_callback kbId={} fileId={} fileName={} oldGroupId={} oldParent={} intendedGroupId={} intendedParent={} versionDate={}",
                        kbId, f.getId(), f.getName(),
                        old == null ? null : old.getGroupId(),
                        old == null ? null : old.getParentFileName(),
                        groupId, parentFileName, versionDate);
            }
        } catch (Exception e) {
            // 审计失败绝不影响归组主流程
            log.warn("R14-C-FIX-16 审计失败 kbId={} groupId={} err={}", kbId, groupId, e.getMessage());
        }
    }

    private String describeFiles(List<FileMultiversion> files) {
        List<String> out = Lists.newArrayList();
        for (FileMultiversion f : files) {
            out.add(f.getId() + ":" + f.getName());
        }
        return out.toString();
    }

    /**
     * R14-C-FIX-01：版本归一键。
     * "R12FIX-product-loan(1).docx" 与 "R12FIX-product-loan.docx" 归一到同一键（同一文档的不同版本）；
     * "R12FIX-credit-ledger.xlsx" 保持自身键（不同文档绝不并组）。扩展名参与比较，避免 .docx/.xlsx 混淆。
     */
    private static String versionKeyOf(String fileName) {
        if (fileName == null)
            return "";
        String name = fileName.trim().replace(" ", "");
        return name.replaceAll("[（(]\\d+[）)](\\.[^.]*)?$", "$1");
    }

    private void updateVersion(String primitiveName, List<Long> ids, String versionDate) {
        ids.forEach(fileId -> {
            Integer pageNo = 1;
            Integer pageSize = 50;
            List<FileChunkDTO> fileChunks = knowledgeBaseFileDomainService.getFileChunks(fileId, pageNo, pageSize);
            if (CollectionUtils.isEmpty(fileChunks))
                return;
            while (true) {
                List<Long> chunkIds = fileChunks.stream().map(FileChunkDTO::getId).collect(Collectors.toList());
                if (!CollectionUtils.isEmpty(chunkIds)) {
                    JSONObject reviseDateParam = buildReviseDateParam(primitiveName, chunkIds, "revise_date", versionDate);
                    //修改向量数据中的修订时间
                    remoteFileUtils.faqUpdateField(JSONObject.toJSONString(reviseDateParam));
                    //更新es中的数据
                    String resp = remoteFileUtils.updateFieldteEs(JSONObject.toJSONString(reviseDateParam));
                    JSONObject respJson = JSONObject.parseObject(resp);
                    if (!Objects.equals(respJson.getInteger("code"), 200))
                        throw new ApplicationException(ErrCodeEnum.UPDATE_ES_ERROR);
                    if (fileChunks.size() < pageSize)
                        break;
                    pageNo++;
                    fileChunks = knowledgeBaseFileDomainService.getFileChunks(fileId, pageNo, pageSize);
                }
            }

        });
    }

    private JSONObject buildReviseDateParam(String primitiveName, List<Long> pks, String colName, Object colValue) {
        JSONObject faqReq = new JSONObject();
        faqReq.put("index_name", primitiveName);
        faqReq.put("pk", pks);
        faqReq.put("col_name", colName);
        faqReq.put("col_value", colValue);
        return faqReq;
    }
}
