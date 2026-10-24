package com.gientech.ragindexservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.baomidou.mybatisplus.core.toolkit.IdWorker;
import com.baomidou.mybatisplus.core.toolkit.StringUtils;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.plugins.pagination.PageDTO;
import com.gientech.ragcommon.auth.enums.BizTypeEnums;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.dto.FaqDTO;
import com.gientech.ragcommon.index.enmus.*;
import com.gientech.ragcommon.index.request.*;
import com.gientech.ragcommon.index.utils.BizLabelUtils;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragindexservice.application.service.BizLabelAppService;
import com.gientech.ragindexservice.application.service.FAQAppService;
import com.gientech.ragindexservice.application.service.ModelInfoAppService;
import com.gientech.ragindexservice.domain.entity.*;
import com.gientech.ragindexservice.domain.service.*;
import com.gientech.ragindexservice.infrastructure.FileParseUtils;
import com.gientech.ragindexservice.infrastructure.RemoteFileUtils;
import com.gientech.ragcommon.index.dto.BizLabelDTO;
import com.gientech.ragcommon.index.request.FaqUpdateReq;
import com.gientech.start.storage.exception.FileStorageException;
import com.gientech.start.storage.model.FileInfo;
import com.gientech.start.storage.utils.FileStorageUtils;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import com.google.common.collect.Sets;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.InputStreamResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;
import org.springframework.web.multipart.MultipartFile;
import java.io.InputStream;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.function.Function;
import java.util.stream.Collectors;

import static com.gientech.ragcommon.index.enmus.FileFieldEnums.FAQ_TABLE_NAME_PREFIX;

@Slf4j
@Service
public class FAQAppServiceImpl implements FAQAppService {

    @Autowired
    private KnowledgeBaseListDomainService knowledgeBaseListDomainService;

    @Autowired
    private KnowledgeBaseDomainService knowledgeBaseDomainService;

    @Autowired
    private FileStorageUtils fileStorageUtils;

    @Autowired
    private RemoteFileUtils remoteFileUtils;

    @Autowired
    private FileParseUtils fileParseUtils;

    @Autowired
    private ChunnkDomainService chunnkDomainService;

    @Autowired
    private ModelInfoAppService modelInfoAppService;

    @Autowired
    private BizLabelDomainService bizLabelDomainService;

    @Autowired
    private BizLabelAppService bizLabelAppService;

    @Autowired
    private FolderInfoDomainService folderInfoDomainService;

    @Override
    public ResponseEntity<InputStreamResource> downloadTemplate(String fileType) throws Exception {
        String templateFileDir = "faqtemplates/";
        String templateFilePath = null;
        if (fileType.equals("xlsx"))
            templateFilePath = templateFileDir + "FAQ模版.xlsx";
        else if (fileType.equals("csv"))
            templateFilePath = templateFileDir + "FAQ模版.csv";
        else if (fileType.equals("txt"))
            templateFilePath = templateFileDir + "FAQ模版.txt";
        ClassPathResource resource = new ClassPathResource(templateFilePath);
        InputStream inputStream = resource.getInputStream();

        String filename = templateFilePath.substring(templateFilePath.indexOf("/") + 1);
        String encodedFilename = URLEncoder.encode(filename, StandardCharsets.UTF_8.toString());
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_OCTET_STREAM);
        headers.setContentDispositionFormData("attachment", encodedFilename);
        return ResponseEntity.ok().headers(headers).body(new InputStreamResource(inputStream));
    }

    @Override
    public Boolean delete(FaqDeleteReq faqDeleteReq) {
        Long kbId = faqDeleteReq.getKbId();
        List<Long> folderIds = faqDeleteReq.getFolderIds();
        List<Long> fileIds = faqDeleteReq.getFileIds();
        List<Long> relatedPks = faqDeleteReq.getRelatedPks();

        List<Long> allFolderIds = Lists.newArrayList();
        List<Long> allFileIds = Lists.newArrayList();
        List<Long> pks = Lists.newArrayList();

        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        String realPrimitiveName = knowledgeBase.getRealPrimitiveName();

        //所有
        if (CollectionUtils.isEmpty(folderIds) && CollectionUtils.isEmpty(fileIds) && CollectionUtils.isEmpty(relatedPks))
            return deleteAll(realPrimitiveName);

        //通过relatedPks查询
        if (!CollectionUtils.isEmpty(relatedPks)) {
            Page<FaqInfo> faqPage = chunnkDomainService.pageList(FaqQueryReq.builder()
                    .primitiveName(knowledgeBase.getPrimitiveName())
                    .relatedPks(relatedPks)
                    .isNeedFolderId(false)
                    .expand(true)
                    .build());
            pks.addAll(faqPage.getRecords().stream().map(FaqInfo::getPk).toList());
        }

        //通过文件夹查询
        if (!CollectionUtils.isEmpty(folderIds)) {
            allFolderIds.addAll(folderIds);
            //查询所有文件夹
            folderInfoDomainService.getChildrenFolderIds(folderIds, allFolderIds);
            //查询所有文件
            List<KnowledgeBaseList> kbFiles = knowledgeBaseListDomainService.findFileByFolder(allFolderIds);
            allFileIds.addAll(kbFiles.stream().map(KnowledgeBaseList::getId).toList());
            //查询faq
            Page<FaqInfo> faqPage = chunnkDomainService.pageList(FaqQueryReq.builder()
                    .primitiveName(knowledgeBase.getPrimitiveName())
                    .folderIds(allFolderIds)
                    .isNeedFolderId(false)
                    .expand(true)
                    .build());
            pks.addAll(faqPage.getRecords().stream().map(FaqInfo::getPk).toList());
        }

        if (!CollectionUtils.isEmpty(fileIds))
            allFileIds.addAll(fileIds);

        //通过文件查询
        if (!CollectionUtils.isEmpty(allFileIds)) {
            Page<FaqInfo> faqPage = chunnkDomainService.pageList(FaqQueryReq.builder()
                    .primitiveName(knowledgeBase.getPrimitiveName())
                    .faqFileIds(allFileIds)
                    .isNeedFolderId(false)
                    .expand(true)
                    .build());
            pks.addAll(faqPage.getRecords().stream().map(FaqInfo::getPk).toList());
        }

        //删除文件夹
        folderInfoDomainService.deleteByIds(allFolderIds);

        //删除文件
        knowledgeBaseListDomainService.deleteByIds(allFileIds);

        //删除FAQ
        chunnkDomainService.deleteFaqByPks(knowledgeBase.getPrimitiveName(), pks);
        return true;
    }

    private Boolean deleteAll(String primitiveName) {
        List<Long> pks = Lists.newArrayList();
        Page<FaqInfo> faqPage = chunnkDomainService.pageList(FaqQueryReq.builder()
                .primitiveName(primitiveName)
                .isNeedFolderId(false)
                .expand(true)
                .build());
        pks.addAll(faqPage.getRecords().stream().map(FaqInfo::getPk).toList());

        //删除FAQ
        chunnkDomainService.deleteFaqByPks(primitiveName, pks);
        return true;
    }

    @Override
    public Page<FaqDTO> listNew(FaqQueryReq queryReq) {
        Integer pageNo = queryReq.getPageNo();
        Integer pageSize = queryReq.getPageSize();

        queryReq.setPageNo(1);
        queryReq.setPageSize(500);
        Page<FaqDTO> faqDTOPage = this.list(queryReq);
        List<FaqDTO> records = faqDTOPage.getRecords();
        if (CollectionUtils.isEmpty(records))
            return null;

        Map<Long, FaqDTO> faqRepeatMap = Maps.newHashMap();
        List<FaqDTO> faqRepeatList = Lists.newArrayList();
        while (true) {
            buildSimilarQuestion(records, faqRepeatMap, faqRepeatList);
            if (records.size() < queryReq.getPageSize())
                break;
            queryReq.setPageNo(queryReq.getPageNo() + 1);
            records = this.list(queryReq).getRecords();
        }

        Integer startIndex = (pageNo - 1) * pageSize;
        Integer endIndex = Math.min(startIndex + pageSize, faqRepeatList.size());
        if (startIndex > endIndex)
            return null;
        int total = faqRepeatList.size();
        List<FaqDTO> resultList = faqRepeatList.subList(startIndex, endIndex);
        Page<FaqDTO> page = new PageDTO<>();
        page.setCurrent(pageNo);
        page.setSize(pageSize);
        page.setPages((total / pageSize) + ((total % pageSize) > 0 ? 1 : 0));
        page.setTotal(total);
        page.setRecords(resultList);
        return page;
    }

    @Override
    public Page<FaqDTO> list(FaqQueryReq queryReq) {
        Long kbId = queryReq.getKbId();
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        Page<FaqDTO> page = new PageDTO<>();
        queryReq.setPrimitiveName(knowledgeBase.getPrimitiveName());
        Page<FaqInfo> pageFaq = chunnkDomainService.pageList(queryReq);
        BeanUtil.copyProperties(pageFaq, page);
        page.setRecords(BeanUtil.copyToList(pageFaq.getRecords(), FaqDTO.class));
        return page;
    }

    private void buildSimilarQuestion(List<FaqDTO> faqs, Map<Long, FaqDTO> faqRepeatMap, List<FaqDTO> faqDTOList) {
        faqs.forEach(faq -> {
            Long relatedPk = faq.getRelatedPk();
            FaqDTO faqDTO = faqRepeatMap.get(relatedPk);
            if (Objects.isNull(faqDTO)) {
                faqDTO = faq;
                faqRepeatMap.put(relatedPk, faqDTO);
                faqDTOList.add(faqDTO);
            } else {
                Integer faqType = faq.getFaqType();
                List<FaqDTO> similarQuestions = faqDTO.getSimilarQuestions();
                if (FaqTypeEnums.SOURCE_FAQ.getCode().equals(faqType)) {
                    //删除之前的数据
                    int index = faqDTOList.indexOf(faqDTO);
                    faqDTOList.remove(faqDTO);
                    //创建相似问
                    List<FaqDTO> newSimilarQuestions = Lists.newArrayList();
                    newSimilarQuestions.addAll(similarQuestions);
                    newSimilarQuestions.add(faqDTO);
                    faqDTO = faq;
                    faqDTO.setSimilarQuestions(newSimilarQuestions);
                    //将新的FAQ加入
                    faqDTOList.add(index, faqDTO);
                } else {
                    faqDTO.getSimilarQuestions().add(faq);
                }
            }
        });
    }

    @Override
    public Boolean uploadFiles(Long kbId, Long folderId, Long fileId, MultipartFile[] files) {
        KnowledgeBase dbKnowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(dbKnowledgeBase)) {
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        }

        String folder = dbKnowledgeBase.getPrimitiveName() + "/faq/";
        List<FileInfo> fileInfos = null;
        try {
            //批量上传文件
            fileInfos = fileStorageUtils.putObjects(folder, files, null);
        } catch (FileStorageException ex) {
            log.error(ex.getMessage(), ex);
            throw new ApplicationException(ErrCodeEnum.PUT_OBJECT_ERROR);
        }
        if(CollectionUtils.isEmpty(fileInfos))
            return false;
        List<String> filePaths = fileInfos.stream().map(FileInfo::getFilePath).toList();
        saveBatchFAQ(filePaths, folderId, fileId, dbKnowledgeBase.getPrimitiveName());
        return true;
    }

    private Map<String, KnowledgeBaseList> convertFileToMap(List<KnowledgeBaseList> dbFiles) {
        Map<String, KnowledgeBaseList> fileMap = Maps.newHashMap();
        if (!CollectionUtils.isEmpty(dbFiles)) {
            dbFiles.forEach(file -> fileMap.put(file.getFilePath(), file));
        }
        return fileMap;
    }

    private Boolean saveBatchFAQ(List<String> filePaths, Long folderId, Long fileId, String primitiveName) {
        filePaths.forEach(filePath -> {
            try {
                Set<String> labels = getLabelByFileIdAndFolderId(fileId, folderId);
                log.info("saveBatchFAQ labels:{}", labels);
                List<Map<String, Object>> faqs = fileParseUtils.getFaqs(filePath);
                JSONObject faqReq = new JSONObject();
                List<JSONObject> faqList = new ArrayList<>(faqs.size());
                for (Map<String, Object> faqData : faqs) {
                    JSONObject faq = new JSONObject();
                    faq.put("page_content", faqData.get("question") + "@@" + faqData.get("answer"));
                    JSONObject metadata = new JSONObject();
                    metadata.put("source", filePath);
                    metadata.put("knowledge_base_name", primitiveName);
                    metadata.put("pk", IdWorker.getId());
                    metadata.put("related_pk", IdWorker.getId());
                    metadata.put("question", faqData.get("question"));
                    metadata.put("answer", faqData.get("answer"));
                    metadata.put("faq_type", FaqTypeEnums.SOURCE_FAQ.getCode());
                    metadata.put("file_id", fileId);
                    metadata.put("document_id", fileId);
                    metadata.put("labels", labels);
                    metadata.put("folder_id", Objects.isNull(folderId) ? fileId : folderId);
                    faq.put("metadata", metadata);
                    faqList.add(faq);
                }
                faqReq.put("collection_name", FAQ_TABLE_NAME_PREFIX + primitiveName);
                faqReq.put("document_list", faqList);
                remoteFileUtils.faqSave(JSONObject.toJSONString(faqReq));
                log.info("faq Save:{}", JSONObject.toJSONString(faqReq));
                //faq保存到es中
                faqReq.remove("collection_name");
                faqReq.put("index_name", FAQ_TABLE_NAME_PREFIX + primitiveName);
                String resp = remoteFileUtils.faqSaveEs(JSONObject.toJSONString(faqReq));
                JSONObject respJson = JSONObject.parseObject(resp);
                if (!respJson.getInteger("code").equals(200))
                    throw new ApplicationException(ErrCodeEnum.FAQ_SAVE_ES_ERROR);
            } catch (Exception e) {
                log.error("问答接口解析失败,文件url:【" + filePath + "】,异常原因:【" + e.getMessage() + "】");
            }
        });
        return true;
    }

    @Override
    public Boolean deleteFileById(List<Long> fileIds) {
        KnowledgeBaseList knowledgeBaseFile = knowledgeBaseListDomainService.findById(fileIds.get(0));
        if (Objects.isNull(knowledgeBaseFile))
            throw new ApplicationException(ErrCodeEnum.KB_FILE_NOT_EXISTS_ERROR);
        Long kbId = knowledgeBaseFile.getKbId();
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        if (knowledgeBaseListDomainService.deleteByIds(fileIds)) {
            String primitiveName = knowledgeBase.getPrimitiveName();
            JSONObject delParam = new JSONObject();
            delParam.put("collection_name", FAQ_TABLE_NAME_PREFIX + primitiveName);
            delParam.put("col_name", "document_id");
            delParam.put("col_values", fileIds.stream().map(id -> id.toString()).collect(Collectors.toList()));
            remoteFileUtils.faqDel(JSONObject.toJSONString(delParam));
//            String resp = remoteFileUtils.faqDel(JSONObject.toJSONString(delParam));
//            JSONObject respJson = JSONObject.parseObject(resp);
//            if(!Objects.equals(respJson.getInteger("code"),200))
//                throw new ApplicationException(ErrCodeEnum.FAQ_DELETE_ERROR);
        }
        return true;
    }

    @Override
    public List<FaqDTO> create(FaqSaveOrUpdateReq createReq) {
        List<FaqDTO> faqDTOS = Lists.newArrayList();
        Long kbId = createReq.getKbId();
        Long folderId = createReq.getFolderId();
        Long fileId = createReq.getFileId();
        List<FaqSaveOrUpdateReq.Faq> faqs = createReq.getFaqs();
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        String primitiveName = knowledgeBase.getPrimitiveName();
        if (!CollectionUtils.isEmpty(faqs))
            faqDTOS = saveFaqBatch(primitiveName, faqs, folderId, fileId, null, FaqTypeEnums.SOURCE_FAQ.getCode());
        return faqDTOS;
    }

    @Override
    public Boolean update(FaqSaveOrUpdateReq updateReq) {
        Long kbId = updateReq.getKbId();
        Long fileId = updateReq.getFileId();
        List<FaqSaveOrUpdateReq.Faq> faqs = updateReq.getFaqs();
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        String primitiveName = knowledgeBase.getPrimitiveName();
        if (!CollectionUtils.isEmpty(faqs))
            updateFaqBatch(primitiveName, faqs, fileId);
        return true;
    }

    @Override
    public Boolean saveOrUpdate(FaqSaveOrUpdateReq saveOrUpdateReq) {
        Long kbId = saveOrUpdateReq.getKbId();
        Long fileId = saveOrUpdateReq.getFileId();
        Long folderId = saveOrUpdateReq.getFolderId();
        List<FaqSaveOrUpdateReq.Faq> faqs = saveOrUpdateReq.getFaqs();
        if (CollectionUtils.isEmpty(faqs))
            return false;
        List<FaqSaveOrUpdateReq.Faq> updateList = new ArrayList<>();
        List<FaqSaveOrUpdateReq.Faq> saveList = new ArrayList<>();

        faqs.forEach(faq -> {
            if (Objects.isNull(faq.getPk()))
                saveList.add(faq);
            else
                updateList.add(faq);
        });
        if (!CollectionUtils.isEmpty(saveList) || !CollectionUtils.isEmpty(updateList)) {
            KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
            if (Objects.isNull(knowledgeBase))
                throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
            String primitiveName = knowledgeBase.getPrimitiveName();
            if (!CollectionUtils.isEmpty(saveList))
                saveFaqBatch(primitiveName, saveList, folderId, fileId, null, FaqTypeEnums.SOURCE_FAQ.getCode());
            if (!CollectionUtils.isEmpty(updateList))
                updateFaqBatch(primitiveName, updateList, fileId);
        }

        return true;
    }

    private void updateFaqBatch(String primitiveName, List<FaqSaveOrUpdateReq.Faq> updateList, Long fileId) {
        String filePath = null;
        if (!Objects.isNull(fileId)) {
            KnowledgeBaseList kbFile = knowledgeBaseListDomainService.findById(fileId);
            filePath = kbFile.getFilePath();
        }
        //向量数据库
        JSONObject faqReq = buildUpdateParam(updateList, primitiveName, fileId, filePath);
        remoteFileUtils.faqUpdate(JSONObject.toJSONString(faqReq));
        String resp = remoteFileUtils.faqUpdateEs(JSONObject.toJSONString(faqReq));
        JSONObject respJson = JSONObject.parseObject(resp);
        if (!Objects.equals(respJson.getInteger("code"), 200))
            throw new ApplicationException(ErrCodeEnum.UPDATE_ES_ERROR);

    }

    private JSONObject buildUpdateParam(List<FaqSaveOrUpdateReq.Faq> updateList, String primitiveName, Long fileId, String filePath) {
        List<FaqInfo> faqInfos = chunnkDomainService.faqList(FaqQueryReq.builder()
                .primitiveName(primitiveName)
                .isNeedFolderId(false)
                .pks(updateList.stream().map(FaqSaveOrUpdateReq.Faq::getPk).toList())
                .build());
        Map<Long,FaqSaveOrUpdateReq.Faq> faqMap = Maps.newHashMap();
        updateList.forEach(faq -> faqMap.put(faq.getPk(),faq));

        for (FaqInfo faqInfo : faqInfos) {
            FaqSaveOrUpdateReq.Faq faq = faqMap.get(faqInfo.getPk());
            if(Objects.isNull(faq))
                continue;
            faqInfo.setKnowledgeBaseName(FAQ_TABLE_NAME_PREFIX + primitiveName);
            faqInfo.setAnswer(faq.getAnswer());
            faqInfo.setQuestion(faq.getQuestion());
            faqInfo.setPageContent(faq.getQuestion() + "@@" + faq.getAnswer());
        }

        JSONObject faqReq = new JSONObject();
        faqReq.put("document_list", faqInfos);
        faqReq.put("index_name", FAQ_TABLE_NAME_PREFIX + primitiveName);
        return faqReq;
    }


    private List<FaqDTO> saveFaqBatch(String primitiveName, List<FaqSaveOrUpdateReq.Faq> saveList, Long folderId, Long fileId, Long relatedPk, Integer faqType) {
        String filePath = null;
        Set<String> labels = null;
        List<FaqDTO> faqDTOS = Lists.newArrayList();
        if (!Objects.isNull(fileId) || !Objects.isNull(folderId)) {
//            KnowledgeBaseList kbFile = knowledgeBaseListDomainService.findById(fileId);
//            filePath = kbFile.getFilePath();
//            labels = bizLabelAppService.findByFileId(kbId, fileId);
            labels = getLabelByFileIdAndFolderId(fileId, folderId);
        }
        JSONObject faqReq = buildSaveParam(saveList, primitiveName, fileId, filePath, relatedPk, faqType, folderId, labels,faqDTOS);
        //milvus数据库
        remoteFileUtils.faqSave(JSONObject.toJSONString(faqReq));
        //es数据库
        faqReq.remove("collection_name");
        faqReq.put("index_name", FAQ_TABLE_NAME_PREFIX + primitiveName);
        String resp = remoteFileUtils.faqSaveEs(JSONObject.toJSONString(faqReq));
        JSONObject respJson = JSONObject.parseObject(resp);
        if (!Objects.equals(respJson.getInteger("code"), 200))
            throw new ApplicationException(ErrCodeEnum.FAQ_SAVE_ES_ERROR);
        return faqDTOS;
    }

    private JSONObject buildSaveParam(
            List<FaqSaveOrUpdateReq.Faq> faqs,
            String primitiveName,
            Long fileId,
            String filePath,
            Long relatedPk,
            Integer faqType,
            Long folderId,
            Set<String> labels,
            List<FaqDTO> faqDTOS
    ) {
        JSONObject faqReq = new JSONObject();
        List<JSONObject> faqList = new ArrayList<>();
        for (FaqSaveOrUpdateReq.Faq item : faqs) {
            long pk = IdWorker.getId();
            Long related = Objects.isNull(relatedPk) ? IdWorker.getId() : relatedPk;
            String pageContent = item.getQuestion() + "@@" + item.getAnswer();
            JSONObject faq = new JSONObject();
            JSONObject metadata = new JSONObject();
            metadata.put("source", "");
            metadata.put("knowledge_base_name", FAQ_TABLE_NAME_PREFIX + primitiveName);
            metadata.put("related_pk", related);
            metadata.put("status", item.getStatus());
            if (!Objects.isNull(fileId)) {
                metadata.put("source", filePath);
                metadata.put("document_id", fileId.toString());
            }
            metadata.put("pk", pk);
            metadata.put("faq_type", faqType);
            metadata.put("folder_id", Objects.isNull(folderId) ? fileId : folderId);
            metadata.put("file_id", fileId);
            metadata.put("document_id", fileId);
            metadata.put("question", item.getQuestion());
            metadata.put("answer", item.getAnswer());
            metadata.put("labels", labels);
            faq.put("page_content", pageContent);
            faq.put("metadata", metadata);
            faqList.add(faq);

            //返回结果
            FaqDTO faqDTO = new FaqDTO();
            faqDTO.setQuestion(item.getQuestion());
            faqDTO.setAnswer(item.getAnswer());
            faqDTO.setRelatedPk(related);
            faqDTO.setPk(pk);
            faqDTOS.add(faqDTO);
        }
        faqReq.put("document_list", faqList);
        faqReq.put("collection_name", FAQ_TABLE_NAME_PREFIX + primitiveName);
        return faqReq;
    }

    private Set<String> getLabelByFileIdAndFolderId(Long fileId, Long folderId) {
        List<Long> folderIds = Objects.isNull(folderId) ? List.of() : List.of(folderId);
        List<Long> fileIds = Objects.isNull(fileId) ? List.of() : List.of(fileId);

        Map<String, String> idLabelMap = bizLabelDomainService.findLabelByFileIdsAndFolderIds(fileIds, folderIds);
        return BizLabelUtils.getLabelArrayByIdLabelMap(idLabelMap, fileId, folderId);
    }

    @Override
    public Boolean similarQuestionAdd(SimilarQuestionReq similarQuestionAddReq) {
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(similarQuestionAddReq.getKbId());
        if (Objects.isNull(knowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        String primitiveName = knowledgeBase.getPrimitiveName();
//        checkSimilarQuestionNums(primitiveName,knowledgeBase.getConfig(),similarQuestionAddReq.getRelatedPk());
//        FaqDTO faqDTO = getFaqs(primitiveName, Arrays.asList(similarQuestionAddReq.getPk()),null).get(0);
        List<FaqInfo> faqs = chunnkDomainService.faqList(
                FaqQueryReq.builder()
                        .primitiveName(primitiveName)
                        .pks(Arrays.asList(similarQuestionAddReq.getPk()))
                        .isNeedFolderId(false)
                        .build());
        FaqInfo faqData = faqs.get(0);
        //保存相似问
        List<FaqSaveOrUpdateReq.Faq> saveList = Lists.newArrayList();
        FaqSaveOrUpdateReq.Faq faq = new FaqSaveOrUpdateReq.Faq();
        faq.setQuestion(similarQuestionAddReq.getSimilarQuestion());
        faq.setAnswer(faqData.getAnswer());
        faq.setStatus(faqData.getStatus());
        saveList.add(faq);
        saveFaqBatch(primitiveName, saveList, null, similarQuestionAddReq.getFileId(), similarQuestionAddReq.getRelatedPk(), FaqTypeEnums.SIMILAR_QUESTION.getCode());
        return true;
    }

    @Override
    public Boolean similarQuestionEdit(SimilarQuestionReq similarQuestionAddReq) {
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(similarQuestionAddReq.getKbId());
        if (Objects.isNull(knowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        String primitiveName = knowledgeBase.getPrimitiveName();
        Long pk = similarQuestionAddReq.getPk();
        String similarQuestion = similarQuestionAddReq.getSimilarQuestion();
        Page<FaqInfo> faqPage = chunnkDomainService.pageList(FaqQueryReq.builder().primitiveName(primitiveName).pks(Arrays.asList(pk)).pageNo(1).pageSize(1).build());
        List<FaqInfo> records = faqPage.getRecords();
        if (CollectionUtils.isEmpty(records))
            throw new ApplicationException(ErrCodeEnum.FAQ_NOT_EXIST_ERROR);
        List<FaqUpdateReq> updateList = Lists.newArrayList();
        records.forEach(faqInfo -> {
            FaqUpdateReq faq = BeanUtil.copyProperties(faqInfo, FaqUpdateReq.class);
            faq.setPageContent(similarQuestion + "@@" + faq.getAnswer());
            faq.setQuestion(similarQuestion);
            updateList.add(faq);
        });
        chunnkDomainService.updateFaqBatch(primitiveName, updateList);
//        chunnkDomainService.updateChunkField(FAQ_TABLE_NAME_PREFIX + primitiveName, Arrays.asList(pk), "page_content", similarQuestion + "@@" + faq.getAnswer());
//        chunnkDomainService.updateChunkField(FAQ_TABLE_NAME_PREFIX + primitiveName, Arrays.asList(pk), "question", similarQuestion);
        return true;
    }

    @Override
    public Set<Set<FaqDTO>> repeatCheck(Long kbId) {
        return repeatCheck(kbId, null);
    }

    private Set<Set<FaqDTO>> repeatCheck(Long kbId, List<Long> relatedpks) {
        Integer pageNo = 1;
        Integer pageSize = 500;
        FaqQueryReq faqQueryReq = FaqQueryReq.builder()
                .pageNo(pageNo)
                .isNeedFolderId(false)
                .pageSize(pageSize)
                .isNeedFolderId(false)
                .faqType(FaqTypeEnums.SOURCE_FAQ.getCode())
                .kbId(kbId)
                .relatedPks(relatedpks)
                .build();
        Map<String, Set<FaqDTO>> faqRepeatMap = Maps.newHashMap();
        Set<Set<FaqDTO>> faqRepeatSet = Sets.newHashSet();
        List<FaqDTO> records = this.list(faqQueryReq).getRecords();
        if (CollectionUtils.isEmpty(records))
            return faqRepeatSet;
        while (true) {
            faqRepeatCheck(records, faqRepeatMap, faqRepeatSet);
            if (records.size() < pageSize)
                break;
            faqQueryReq.setPageNo(faqQueryReq.getPageNo() + 1);
            records = this.list(faqQueryReq).getRecords();
        }
        return faqRepeatSet;
    }

    private void faqRepeatCheck(List<FaqDTO> faqDTOS, Map<String, Set<FaqDTO>> faqRepeatMap, Set<Set<FaqDTO>> faqRepeatSet) {
        faqDTOS.forEach(faqDTO -> {
            String question = faqDTO.getQuestion();
            Set<FaqDTO> faqSet = faqRepeatMap.get(question);
            if (CollectionUtils.isEmpty(faqSet)) {
                faqSet = Sets.newHashSet();
                faqSet.add(faqDTO);
                faqRepeatMap.put(question, faqSet);
            } else
                faqSet.add(faqDTO);
            if (faqSet.size() == 2)
                faqRepeatSet.add(faqSet);
        });
    }

    @Override
    public Set<Set<FaqDTO>> changeStatus(FaqStatusUpdateReq faqStatusUpdateReq) {
        Long kbId = faqStatusUpdateReq.getKbId();
        List<Long> folderIds = faqStatusUpdateReq.getFolderIds();
        List<Long> fileIds = faqStatusUpdateReq.getFileIds();
        List<Long> relatedpks = faqStatusUpdateReq.getRelatedpks();
        List<Long> allRelatedpks = Lists.newArrayList();

        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        faqStatusUpdateReq.setPrimitiveName(knowledgeBase.getPrimitiveName());

        //启用/禁用所有
        if (CollectionUtils.isEmpty(folderIds) && CollectionUtils.isEmpty(fileIds) && CollectionUtils.isEmpty(relatedpks))
           return changeAllStatus(faqStatusUpdateReq);

        //启用/禁用指定的faq
        if (!CollectionUtils.isEmpty(relatedpks))
            allRelatedpks.addAll(relatedpks);

        //获取文件夹中的子文件夹
        List<Long> allFolderIds = Lists.newArrayList();
        List<Long> allFileIds = Lists.newArrayList();
        if (!CollectionUtils.isEmpty(folderIds))
            allFolderIds.addAll(folderIds);

        //启用/禁用指定文件夹下的faq
        if (!CollectionUtils.isEmpty(allFolderIds)) {
            folderInfoDomainService.getChildrenFolderIds(folderIds, allFolderIds);
            List<KnowledgeBaseList> kbFiles = knowledgeBaseListDomainService.findFileByFolder(allFolderIds);
            allFileIds.addAll(kbFiles.stream().map(KnowledgeBaseList::getId).toList());
            Page<FaqInfo> faqPage = chunnkDomainService.pageList(FaqQueryReq.builder()
                    .primitiveName(knowledgeBase.getPrimitiveName())
                    .folderIds(allFolderIds)
                    .isNeedFolderId(false)
                    .expand(true)
                    .build());
            allRelatedpks.addAll(faqPage.getRecords().stream().map(FaqInfo::getRelatedPk).toList());
        }

        //启用/禁用指定文件下的faq
        if (!CollectionUtils.isEmpty(fileIds))
            allFileIds.addAll(fileIds);
        if (!CollectionUtils.isEmpty(allFileIds)) {
            Page<FaqInfo> faqPage = chunnkDomainService.pageList(FaqQueryReq.builder()
                    .primitiveName(knowledgeBase.getPrimitiveName())
                    .faqFileIds(allFileIds)
                    .isNeedFolderId(false)
                    .expand(true)
                    .build());
            allRelatedpks.addAll(faqPage.getRecords().stream().map(FaqInfo::getRelatedPk).toList());
        }

        faqStatusUpdateReq.setRelatedpks(allRelatedpks);
        return changeFqaStatus(faqStatusUpdateReq);
    }

    private Set<Set<FaqDTO>> changeFqaStatus(FaqStatusUpdateReq faqStatusUpdateReq) {
        Long kbId = faqStatusUpdateReq.getKbId();
        Integer status = faqStatusUpdateReq.getStatus();
        List<Long> relatedpks = faqStatusUpdateReq.getRelatedpks();
        List<Long> disabledRelatedpks = faqStatusUpdateReq.getDisabledRelatedpks();
        String primitiveName = faqStatusUpdateReq.getPrimitiveName();
        List<FaqDTO> enabledFaqs = null;

        //禁用操作
        if(FaqStatusEnums.DISABLED.getCode().equals(status)){
            Page<FaqInfo> faqPage = chunnkDomainService.pageList(
                    FaqQueryReq.builder()
                            .isNeedFolderId(false)
                            .primitiveName(primitiveName)
                            .relatedPks(relatedpks)
                            .build());
            List<FaqInfo> faqs = faqPage.getRecords();
            updateFaqStatus(primitiveName, faqs.stream().map(FaqInfo::getPk).collect(Collectors.toList()), status);
            return null;
        }else if (FaqStatusEnums.ENABLED.getCode().equals(status) && CollectionUtils.isEmpty(disabledRelatedpks)) {
            //启用需要校验faq的重复性
            List<FaqInfo> faqs = chunnkDomainService.faqList(
                    FaqQueryReq.builder()
                            .isNeedFolderId(false)
                            .faqType(FaqTypeEnums.SOURCE_FAQ.getCode())
                            .primitiveName(primitiveName)
                            .relatedPks(relatedpks)
                            .build());
            enabledFaqs = BeanUtil.copyToList(faqs, FaqDTO.class);

            Integer pageNo = 1;
            Integer pageSize = 500;
            FaqQueryReq faqQuery = FaqQueryReq.builder()
                    .isNeedFolderId(false)
                    .kbId(kbId)
                    .faqType(FaqTypeEnums.SOURCE_FAQ.getCode())
                    .status(FaqStatusEnums.ENABLED.getCode())
                    .pageNo(pageNo)
                    .pageSize(pageSize)
                    .build();
            Page<FaqDTO> faqDTOPage = this.list(faqQuery);
            List<FaqDTO> dbFaqList = faqDTOPage.getRecords();
            List<FaqDTO> faqDTOList = Lists.newArrayList();
            faqDTOList.addAll(enabledFaqs);
            while (true) {
                faqDTOList.addAll(dbFaqList);
                if (dbFaqList.size() < pageSize)
                    break;
                faqQuery.setPageNo(faqQuery.getPageNo() + 1);
                dbFaqList = this.list(faqQuery).getRecords();
            }
            Map<String, Set<FaqDTO>> faqRepeatMap = Maps.newHashMap();
            Set<Set<FaqDTO>> faqRepeatSet = Sets.newHashSet();
            //与启用的faq对比
            faqRepeatCheck(faqDTOList, faqRepeatMap, faqRepeatSet);
            //返回重复的数据
            if (!CollectionUtils.isEmpty(faqRepeatSet)) return faqRepeatSet;
        }

        //启用 需要禁用重复的faq
        if (!CollectionUtils.isEmpty(disabledRelatedpks)) {
            Page<FaqInfo> faqPage = chunnkDomainService.pageList(
                    FaqQueryReq.builder()
                            .isNeedFolderId(false)
                            .primitiveName(primitiveName)
                            .relatedPks(disabledRelatedpks)
                            .build());
            List<FaqInfo> faqs = faqPage.getRecords();
            List<Long> disabledPks = faqs.stream().map(FaqInfo::getPk).collect(Collectors.toList());
            updateFaqStatus(primitiveName, disabledPks, FaqStatusEnums.DISABLED.getCode());
            //移除禁用的faq
            relatedpks.removeAll(disabledPks);
        }

        if (!CollectionUtils.isEmpty(relatedpks)) {
            Page<FaqInfo> faqPage = chunnkDomainService.pageList(
                    FaqQueryReq.builder()
                            .isNeedFolderId(false)
                            .primitiveName(primitiveName)
                            .relatedPks(relatedpks)
                            .build());
            List<FaqInfo> faqs = faqPage.getRecords();
            List<Long> enabledPks = faqs.stream().map(FaqInfo::getPk).collect(Collectors.toList());
            updateFaqStatus(primitiveName, enabledPks, status);
        }
        return null;
    }

    private Set<Set<FaqDTO>> changeAllStatus(FaqStatusUpdateReq faqStatusUpdateReq) {
        Long kbId = faqStatusUpdateReq.getKbId();
        Integer status = faqStatusUpdateReq.getStatus();
        List<Long> disabledRelatedpks = faqStatusUpdateReq.getDisabledRelatedpks();
        List<Long> relatedpks = faqStatusUpdateReq.getRelatedpks();
        String primitiveName = faqStatusUpdateReq.getPrimitiveName();

        if (FaqStatusEnums.ENABLED.getCode().equals(status) && CollectionUtils.isEmpty(disabledRelatedpks)) {
            //返回重复的faq
            Set<Set<FaqDTO>> repeatData = repeatCheck(kbId, relatedpks);
            if (!CollectionUtils.isEmpty(repeatData))
                return repeatData;
        }

        Integer pageNo = 1;
        Integer pageSize = 500;
        FaqQueryReq faqQuery = FaqQueryReq.builder()
                .kbId(kbId)
                .isNeedFolderId(false)
                .status(FaqStatusEnums.ENABLED.getCode().equals(status) ? FaqStatusEnums.DISABLED.getCode() : FaqStatusEnums.ENABLED.getCode())
                .pageNo(pageNo)
                .pageSize(pageSize)
                .build();
        Page<FaqDTO> faqDTOPage = this.list(faqQuery);
        List<FaqDTO> dbFaqList = faqDTOPage.getRecords();
        List<FaqDTO> faqDTOList = Lists.newArrayList();
        if(CollectionUtils.isEmpty(dbFaqList))
            return null;
        while (true) {
            faqDTOList.addAll(dbFaqList);
            if (dbFaqList.size() < pageSize)
                break;
            faqQuery.setPageNo(faqQuery.getPageNo() + 1);
            dbFaqList = this.list(faqQuery).getRecords();
        }

        List<Long> pks = faqDTOList.stream().map(FaqDTO::getPk).collect(Collectors.toList());
        if (!CollectionUtils.isEmpty(disabledRelatedpks)) {
            //需要禁用的faq
            List<FaqInfo> faqs = chunnkDomainService.faqList(
                    FaqQueryReq.builder()
                            .primitiveName(primitiveName)
                            .kbId(kbId)
                            .isNeedFolderId(false)
                            .relatedPks(disabledRelatedpks).build());
            //需要禁用的faq的id
            List<Long> disabledPks = faqs.stream().map(FaqInfo::getPk).collect(Collectors.toList());
            updateFaqStatus(primitiveName, disabledPks, FaqStatusEnums.DISABLED.getCode());
            pks.removeAll(disabledPks);
        }

        if (!CollectionUtils.isEmpty(pks))
            updateFaqStatus(faqStatusUpdateReq.getPrimitiveName(), pks, status);
        return null;
    }

    private void updateFaqStatus(String primitiveName, List<Long> pks, Integer status) {
        //更新es和milvus的faq启用或禁用状态
        chunnkDomainService.updateChunkField(FAQ_TABLE_NAME_PREFIX + primitiveName, pks, "status", status);
    }

    @Override
    public List<FaqDTO> polish(FaqPolishReq faqPolishReq) {
        Long kbId = faqPolishReq.getKbId();
        Long fileId = faqPolishReq.getFileId();
        List<Long> pks = faqPolishReq.getPks();
        KnowledgeBase kb = knowledgeBaseDomainService.findByKbId(kbId);
        String faqModelName = kb.getFaqModelName();
        if (Objects.isNull(kb))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        KnowledgeBaseList kbFile = knowledgeBaseListDomainService.findById(fileId);
        //查询FAQ
        Page<FaqInfo> faqPage = chunnkDomainService.pageList(
                FaqQueryReq.builder()
                        .isNeedFolderId(false)
                        .primitiveName(kb.getPrimitiveName())
                        .pks(pks).pageNo(1).pageSize(10000).build());
        List<FaqInfo> faqs = faqPage.getRecords();
        if (!CollectionUtils.isEmpty(faqs)) {
            JSONObject faqReq = buildPolishParm(kbFile, faqs, kb.getPrimitiveName(),faqModelName);
            String resp = remoteFileUtils.faqPolish(JSONObject.toJSONString(faqReq));
            JSONObject respJson = JSONObject.parseObject(resp);
            if (!Objects.equals(respJson.getInteger("code"), 200))
                throw new ApplicationException(ErrCodeEnum.FAQ_POLISH_ERROR.getErrCode(), respJson.getString("msg"));
            return buildPolishData(respJson);
        }
        return null;
    }

    private List<FaqDTO> buildPolishData(JSONObject respJson) {
        List<FaqDTO> faqDTOS = Lists.newArrayList();
        JSONObject data = respJson.getJSONObject("data");
        JSONArray predDictList = data.getJSONArray("pred_dict_list");
        if (!CollectionUtils.isEmpty(predDictList)) {
            predDictList.forEach(faq -> {
                JSONObject faqJson = (JSONObject) faq;
                FaqDTO faqDTO = new FaqDTO();
                faqDTO.setQuestion(faqJson.getString("question"));
                faqDTO.setAnswer(faqJson.getString("answer"));
                faqDTOS.add(faqDTO);
            });
        }
        return faqDTOS;
    }

    private JSONObject buildPolishParm(KnowledgeBaseList kbFile, List<FaqInfo> faqs, String primitiveName,String faqModelName) {
        JSONObject faqReq = new JSONObject();
        JSONArray documentList = new JSONArray();
        faqs.forEach(faq -> {
            JSONObject document = new JSONObject();
            document.put("page_content", faq.getPageContent());

            JSONObject metadata = new JSONObject();
            metadata.put("question", faq.getQuestion());
            metadata.put("answer", faq.getAnswer());
            metadata.put("source", Objects.isNull(kbFile) ? "" : kbFile.getConvertedFilePath());
            metadata.put("document_id", Objects.isNull(kbFile) ? "" : kbFile.getId());
            metadata.put("knowledge_base_name", FAQ_TABLE_NAME_PREFIX + primitiveName);
            document.put("metadata", metadata);
            documentList.add(document);
        });
        faqReq.put("to_database", "false");
        faqReq.put("document_list", documentList);
        faqReq.put("model_info", modelInfoAppService.getSimpByModeName(faqModelName));
        return faqReq;
    }

    @Override
    public Boolean genSimilarQuestion(GenSimilarQuestionReq req) {
        Long kbId = req.getKbId();
        List<Long> folderIds = req.getFolderIds();
        List<Long> fileIds = req.getFileIds();
        List<Long> relatedPks = req.getRelatedPks();

        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        String config = knowledgeBase.getConfig();
        String primitiveName = knowledgeBase.getPrimitiveName();
        String faqModelName = knowledgeBase.getFaqModelName();
        Integer genQuestionNum = null;
        if (StringUtils.isNotBlank(config)) {
            JSONObject confJson = JSON.parseObject(config);
            Integer similarQuestionMaxNums = confJson.getInteger("similarQuestionMaxNums");
            genQuestionNum = Objects.isNull(similarQuestionMaxNums) ? 1 : similarQuestionMaxNums;
        }

        //生成知识库下所有的faq相似问
        if (CollectionUtils.isEmpty(folderIds) && CollectionUtils.isEmpty(fileIds) && CollectionUtils.isEmpty(relatedPks)) {
            Page<FaqInfo> faqPage = chunnkDomainService.pageList(FaqQueryReq.builder()
                    .primitiveName(primitiveName)
                    .isNeedFolderId(false)
                    .faqType(FaqTypeEnums.SOURCE_FAQ.getCode())
                    .expand(true)
                    .build());
            genSimiQuestionQuestion(faqPage.getRecords(), genQuestionNum, primitiveName,faqModelName);
            return true;
        }

        if (!CollectionUtils.isEmpty(relatedPks)) {
            Page<FaqInfo> faqPage = chunnkDomainService.pageList(FaqQueryReq.builder()
                    .primitiveName(primitiveName)
                    .relatedPks(relatedPks)
                    .faqType(FaqTypeEnums.SOURCE_FAQ.getCode())
                    .isNeedFolderId(false)
                    .expand(true)
                    .build());
            genSimiQuestionQuestion(faqPage.getRecords(), genQuestionNum, primitiveName,faqModelName);
        }

        //获取文件夹中的子文件夹
        List<Long> allFolderIds = Lists.newArrayList();
        //获取文件夹中的子文件
        List<Long> allFileIds = Lists.newArrayList();
        if (!CollectionUtils.isEmpty(folderIds)) {
            allFolderIds.addAll(folderIds);
            folderInfoDomainService.getChildrenFolderIds(folderIds, allFolderIds);
            List<KnowledgeBaseList> kbFiles = knowledgeBaseListDomainService.findFileByKbId(kbId, ParseTypeEnums.FAQ_MANAGEMENT.getCode());
            allFileIds.addAll(kbFiles.stream().map(KnowledgeBaseList::getId).collect(Collectors.toList()));
        }

        //所有的文件
        if (!CollectionUtils.isEmpty(fileIds))
            allFileIds.addAll(fileIds);

        //文件夹
        if (!CollectionUtils.isEmpty(allFolderIds)) {
            Page<FaqInfo> faqPage = chunnkDomainService.pageList(FaqQueryReq.builder()
                    .primitiveName(primitiveName)
                    .isNeedFolderId(false)
                    .folderIds(allFolderIds)
                    .faqType(FaqTypeEnums.SOURCE_FAQ.getCode())
                    .expand(true)
                    .build());
            genSimiQuestionQuestion(faqPage.getRecords(), genQuestionNum, primitiveName,faqModelName);
        }

        //文件
        if (!CollectionUtils.isEmpty(allFileIds)) {
            Page<FaqInfo> faqPage = chunnkDomainService.pageList(FaqQueryReq.builder()
                    .primitiveName(primitiveName)
                    .isNeedFolderId(false)
                    .faqFileIds(allFileIds)
                    .faqType(FaqTypeEnums.SOURCE_FAQ.getCode())
                    .expand(true)
                    .build());
            genSimiQuestionQuestion(faqPage.getRecords(), genQuestionNum, primitiveName,faqModelName);
        }

        return true;
    }

    private void genSimiQuestionQuestion(List<FaqInfo> faqInfos, Integer genQuestionNum, String primitiveName,String faqModelName) {
        //查询相似问
        if (!CollectionUtils.isEmpty(faqInfos)) {
            List<FaqDTO> faqDTOS = BeanUtil.copyToList(faqInfos, FaqDTO.class);
            faqDTOS.forEach(faqDTO -> {
                Long relatedPk = faqDTO.getRelatedPk();
                Page<FaqInfo> similarQuestionPage = chunnkDomainService.pageList(FaqQueryReq.builder()
                        .primitiveName(primitiveName)
                        .isNeedFolderId(false)
                        .relatedPks(Arrays.asList(relatedPk))
                        .faqType(FaqTypeEnums.SIMILAR_QUESTION.getCode())
                        .expand(true)
                        .build());
                faqDTO.setSimilarQuestions(BeanUtil.copyToList(similarQuestionPage.getRecords(), FaqDTO.class));
            });
            JSONObject genQuestionReq = buildGenQuestionParam(faqDTOS, genQuestionNum, primitiveName,faqModelName);
            String resp = remoteFileUtils.faqSimiQuestion(JSONObject.toJSONString(genQuestionReq));
            JSONObject respJson = JSONObject.parseObject(resp);
            if (!Objects.equals(respJson.getInteger("code"), 200))
                throw new ApplicationException(ErrCodeEnum.FAQ_GEN_SIMILAR_QUESTION_ERROR.getErrCode(), respJson.getString("msg"));
        }
    }

    private JSONObject buildGenQuestionParam(List<FaqDTO> faqDTOS, Integer genQuestionNum, String primitiveName,String faqModelName) {
        JSONObject genQuestionReq = new JSONObject();
        genQuestionReq.put("model_info", modelInfoAppService.getSimpByModeName(faqModelName));

        genQuestionReq.put("gen_question_num", genQuestionNum);

        JSONArray sourceList = new JSONArray();
        faqDTOS.forEach(faqDTO -> {
            JSONObject source = new JSONObject();
            List<String> simiQuestions = faqDTO.getSimilarQuestions().stream().map(FaqDTO::getQuestion).collect(Collectors.toList());
            source.put("simi_question", simiQuestions);
            source.put("page_content", faqDTO.getPageContent());
            JSONObject metadata = faqDTO.getMetadata();
            metadata.put("knowledge_base_name", FAQ_TABLE_NAME_PREFIX + primitiveName);
            source.put("metadata", faqDTO.getMetadata());
            sourceList.add(source);
        });
        genQuestionReq.put("source_list", sourceList);
        return genQuestionReq;
    }

    @Override
    public FaqDTO getFaqByRelatedPk(FaqQueryReq queryReq) {
        Long kbId = queryReq.getKbId();
        List<Long> relatedPks = queryReq.getRelatedPks();
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        queryReq.setPrimitiveName(knowledgeBase.getPrimitiveName());
        queryReq.setRelatedPks(relatedPks);
        queryReq.setPageNo(1);
        queryReq.setPageSize(500);
        Page<FaqInfo> faqPage = chunnkDomainService.pageList(queryReq);
        List<FaqInfo> records = faqPage.getRecords();
        FaqDTO faqDTO = null;
        if (!CollectionUtils.isEmpty(records)) {
            FaqInfo faq = records.get(records.size() - 1);
            records.remove(faq);
            faqDTO = BeanUtil.copyProperties(faq, FaqDTO.class);
            faqDTO.setSimilarQuestions(BeanUtil.copyToList(records, FaqDTO.class));
        }
        return faqDTO;
    }

    @Override
    public Boolean similarQuestionDel(DelSimilarQuestionReq req) {
        Long kbId = req.getKbId();
        List<Long> folderIds = req.getFolderIds();
        List<Long> fileIds = req.getFileIds();
        List<Long> relatedPks = req.getRelatedPks();

        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);

        //删除所有相似问
        if (CollectionUtils.isEmpty(folderIds) && CollectionUtils.isEmpty(fileIds) && CollectionUtils.isEmpty(relatedPks)) {
            Page<FaqInfo> faqPage = chunnkDomainService.pageList(FaqQueryReq.builder()
                    .primitiveName(knowledgeBase.getPrimitiveName())
                    .faqType(FaqTypeEnums.SIMILAR_QUESTION.getCode())
                    .isNeedFolderId(false)
                    .build());
            chunnkDomainService.deleteFaqByPks(knowledgeBase.getPrimitiveName(), faqPage.getRecords().stream().map(FaqInfo::getPk).collect(Collectors.toList()));
            return true;
        }

        //通过pk删除
        if (!CollectionUtils.isEmpty(relatedPks)) {
            Page<FaqInfo> faqPage = chunnkDomainService.pageList(FaqQueryReq.builder()
                    .primitiveName(knowledgeBase.getPrimitiveName())
                    .relatedPks(relatedPks)
                    .faqType(FaqTypeEnums.SIMILAR_QUESTION.getCode())
                    .isNeedFolderId(false)
                    .build());
            chunnkDomainService.deleteFaqByPks(knowledgeBase.getPrimitiveName(), faqPage.getRecords().stream().map(FaqInfo::getPk).toList());
        }

        //获取文件夹中的子文件夹
        List<Long> allFolderIds = Lists.newArrayList();
        //获取文件夹中的子文件
        List<Long> allFileIds = Lists.newArrayList();
        if (!CollectionUtils.isEmpty(folderIds))
            allFolderIds.addAll(folderIds);
        if (!CollectionUtils.isEmpty(allFolderIds)) {
            folderInfoDomainService.getChildrenFolderIds(folderIds, allFolderIds);
            List<KnowledgeBaseList> kbFiles = knowledgeBaseListDomainService.findFileByFolder(allFolderIds);
            allFileIds.addAll(kbFiles.stream().map(KnowledgeBaseList::getId).toList());
            Page<FaqInfo> faqPage = chunnkDomainService.pageList(FaqQueryReq.builder()
                    .primitiveName(knowledgeBase.getPrimitiveName())
                    .folderIds(allFolderIds)
                    .faqType(FaqTypeEnums.SIMILAR_QUESTION.getCode())
                    .isNeedFolderId(false)
                    .expand(true)
                    .build());
            chunnkDomainService.deleteFaqByPks(knowledgeBase.getPrimitiveName(), faqPage.getRecords().stream().map(FaqInfo::getPk).collect(Collectors.toList()));
        }

        if (!CollectionUtils.isEmpty(fileIds))
            allFileIds.addAll(fileIds);
        if (!CollectionUtils.isEmpty(allFileIds)) {
            Page<FaqInfo> faqPage = chunnkDomainService.pageList(FaqQueryReq.builder()
                    .primitiveName(knowledgeBase.getPrimitiveName())
                    .faqFileIds(allFileIds)
                    .faqType(FaqTypeEnums.SIMILAR_QUESTION.getCode())
                    .isNeedFolderId(false)
                    .expand(true)
                    .build());
            chunnkDomainService.deleteFaqByPks(knowledgeBase.getPrimitiveName(), faqPage.getRecords().stream().map(FaqInfo::getPk).collect(Collectors.toList()));
        }
        return true;
    }

    @Override
    public Page<FaqDTO> faqList(FaqQueryReq queryReq) {
        Page<FaqDTO> page = new Page<>();
        List<FaqDTO> faqDTOList = Lists.newArrayList();
        Integer pageNo = queryReq.getPageNo();
        Integer pageSize = queryReq.getPageSize();
        String fuzzy = queryReq.getFuzzy();
        Integer basicPermission = knowledgeBaseDomainService.getHighestPermission(queryReq.getKbId());
        //从数据库中查询文件件和文件(先查文件夹在查文件)
        Page<KbFileExt> kbFileExtPage = knowledgeBaseListDomainService.folderAndFileList(FolderAndFilerReq
                        .builder()
                        .userId(Long.parseLong(UserContext.getUser().getUserId()))
                        .kbId(queryReq.getKbId())
                        .folderId(queryReq.getFolderId())
                        .fileId(queryReq.getFileId())
                        .fuzzy(queryReq.getFuzzy()).build(),
                pageNo,
                pageSize
        );
        List<KbFileExt> kbFileExts = kbFileExtPage.getRecords();
        //文件夹和文件转换FAQdto
        kbFileExtConvertFaq(faqDTOList, kbFileExts);

        Long kbFileExtTotal = kbFileExtPage.getTotal();
        Integer kbFileExtsSize = CollectionUtils.isEmpty(kbFileExts) ? 0 : kbFileExts.size();
        Long faqTotal = 0L;
        //pageSize和文件夹和文件的数量进行比较 如果pageSize<文件夹和文件的数量 从es中查询faq
        if (kbFileExtsSize < pageSize) {
            Long kbId = queryReq.getKbId();
            KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
            if (Objects.isNull(knowledgeBase))
                throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);

            Page<FaqInfo> faqInfoPage = null;
            if (StringUtils.isNotBlank(fuzzy)) {
                faqInfoPage = chunnkDomainService.pageList(FaqQueryReq.builder()
                        .kbId(queryReq.getKbId())
                        .primitiveName(knowledgeBase.getPrimitiveName())
                        .fuzzy(queryReq.getFuzzy())
                        .pks(queryReq.getPks())
                        .relatedPks(queryReq.getRelatedPks())
                        .status(queryReq.getStatus())
                        .folderId(queryReq.getFolderId())
                        .faqFileIds(Objects.isNull(queryReq.getFileId()) ? null : List.of(queryReq.getFileId()))
//                    .isNeedFolderId(false)
                        .faqType(FaqTypeEnums.SOURCE_FAQ.getCode())
//                        .pageNo((kbFileExtsSize != 0) ? 1 : pageNo)
//                        .pageSize(pageSize)
                        .build());
                List<FaqInfo> records = faqInfoPage.getRecords();
                faqInfoPage.setRecords(records.stream().filter(record -> record.getPageContent().contains(fuzzy)).toList());
                faqInfoPage.setTotal(faqInfoPage.getRecords().size());
            } else {
                faqInfoPage = chunnkDomainService.pageList(FaqQueryReq.builder()
                        .kbId(queryReq.getKbId())
                        .primitiveName(knowledgeBase.getPrimitiveName())
                        .fuzzy(queryReq.getFuzzy())
                        .pks(queryReq.getPks())
                        .relatedPks(queryReq.getRelatedPks())
                        .status(queryReq.getStatus())
                        .folderId(queryReq.getFolderId())
                        .faqFileIds(Objects.isNull(queryReq.getFileId()) ? null : List.of(queryReq.getFileId()))
//                    .isNeedFolderId(false)
                        .faqType(FaqTypeEnums.SOURCE_FAQ.getCode())
                        .pageNo((kbFileExtsSize != 0) ? 1 : pageNo)
                        .pageSize(pageSize)
                        .build());
            }

            List<FaqInfo> faqRecords = faqInfoPage.getRecords();
            faqTotal = faqInfoPage.getTotal();
            faqRecords = faqRecords.subList(0, Math.toIntExact(Math.min(faqRecords.size(), pageSize - kbFileExtsSize)));
            faqInfoConvertFaq(faqDTOList, faqRecords, kbId, knowledgeBase.getPrimitiveName());
        }
        setFaqLabelAndPermission(faqDTOList, basicPermission, queryReq.getKbId());
        page.setRecords(faqDTOList);
        page.setTotal(kbFileExtTotal + faqTotal);
        page.setCurrent(pageNo);
        page.setPages(pageSize);
        return page;
    }


    private void setFaqLabelAndPermission(List<FaqDTO> faqDTOList, Integer basicPermission, Long kbId) {
        Set<Long> folderIds = faqDTOList.stream().filter(faq -> faq.getDataType().equals(1)).map(FaqDTO::getCommonId).collect(Collectors.toSet());
        Set<Long> fileIds = faqDTOList.stream().filter(faq -> faq.getDataType().equals(2)).map(FaqDTO::getCommonId).collect(Collectors.toSet());
        List<KnowledgeBaseList> filesWithPermission = knowledgeBaseListDomainService.queryListWithPermission(kbId, FolderTypeEnums.FAQ_MANAGEMENT.getCode(), ParseTypeEnums.FAQ_MANAGEMENT.getCode(), getFaqManagementTypes());
        Map<Long, KnowledgeBaseList> permissionMap = getPermissionMap(filesWithPermission);

        Map<String, String> labelByFileIdsAndFolderIds = bizLabelDomainService.findLabelByFileIdsAndFolderIds(new ArrayList<>(fileIds), new ArrayList<>(folderIds));

        faqDTOList.forEach(faq -> {
            faq.setLabelsByLabel(labelByFileIdsAndFolderIds.get(faq.getCommonIdStr()));
            setPermission(faq, basicPermission, permissionMap);
        });
    }

    private List<Integer> getFaqManagementTypes() {
        return List.of(BizTypeEnums.FAQ.getCode(), BizTypeEnums.FAQ_FILE.getCode(), BizTypeEnums.FAQ_FOLDER.getCode());
    }

    private Map<Long, KnowledgeBaseList> getPermissionMap(List<KnowledgeBaseList> filesWithPermission) {
        Map<Long, KnowledgeBaseList> permissionMap = filesWithPermission.stream().collect(Collectors.toMap(KnowledgeBaseList::getCommonId, Function.identity(), (v1, v2) -> v1));
        Map<Long, KnowledgeBaseList> relatedPermissionMap = Maps.newHashMap();
        for (Map.Entry<Long, KnowledgeBaseList> entry : permissionMap.entrySet()) {
            if (Objects.nonNull(folderInfoDomainService.findById(entry.getKey()))) {
                List<KnowledgeBaseList> knowledgeBaseLists = knowledgeBaseListDomainService.recursiveByFolderId(entry.getKey());
                knowledgeBaseLists.forEach(file -> {
                    file.setPermission(entry.getValue().getPermission());
                    relatedPermissionMap.put(file.getId(), file);
                });
            }
        }
        permissionMap.putAll(relatedPermissionMap);
        return permissionMap;
    }

    private void setPermission(FaqDTO faqDTO, Integer basicPermission, Map<Long, KnowledgeBaseList> permissionMap) {
        //查询关联的文件/文件夹权限
        faqDTO.setPermission(basicPermission);
        KnowledgeBaseList knowledgeBaseList = permissionMap.get(faqDTO.getCommonId());
        if (faqDTO.getDataType().equals(FaqListDataTypeEnums.FAQ.getCode())) {
            knowledgeBaseList = permissionMap.get(faqDTO.getFolderId());
        }

        if (Objects.nonNull(knowledgeBaseList) && (basicPermission < knowledgeBaseList.getPermission())) {
            faqDTO.setPermission(knowledgeBaseList.getPermission());
        }
    }

    private void faqInfoConvertFaq(List<FaqDTO> faqDTOList, List<FaqInfo> faqRecords, Long kbId, String primitiveName) {
        if (CollectionUtils.isEmpty(faqRecords))
            return;
        List<FaqDTO> faqDTOs = BeanUtil.copyToList(faqRecords, FaqDTO.class);
        //查询相似问
        faqDTOs.forEach(faqDTO -> {
            Page<FaqInfo> faqInfoPage = chunnkDomainService.pageList(FaqQueryReq.builder()
                    .kbId(kbId)
                    .primitiveName(primitiveName)
                    .relatedPks(Collections.singletonList(faqDTO.getRelatedPk()))
                    .faqType(FaqTypeEnums.SIMILAR_QUESTION.getCode())
                    .isNeedFolderId(false)
                    .pageNo(1)
                    .pageSize(1000)
                    .build());
            faqDTO.setSimilarQuestions(BeanUtil.copyToList(faqInfoPage.getRecords(), FaqDTO.class));
        });
        faqDTOList.addAll(faqDTOs);
    }

    private void kbFileExtConvertFaq(List<FaqDTO> faqDTOList, List<KbFileExt> kbFileExts) {
        if (CollectionUtils.isEmpty(kbFileExts))
            return;
        kbFileExts.forEach(kbFileExt -> {
            FaqDTO faqDTO = BeanUtil.copyProperties(kbFileExt, FaqDTO.class);
            faqDTO.setFileId(kbFileExt.getId());
            faqDTO.setDataType(kbFileExt.getIsFolder() == 1 ? FaqListDataTypeEnums.FOLDER.getCode() : FaqListDataTypeEnums.FILE.getCode());
            faqDTOList.add(faqDTO);
        });
    }

    @Override
    public Boolean transferFaq(FaqTransferReq faqTransferReq) {
        Long kbId = faqTransferReq.getKbId();
        List<Long> folderIds = faqTransferReq.getFolderIds();
        List<Long> fileIds = faqTransferReq.getFileIds();
        List<Long> relatedpks = faqTransferReq.getRelatedpks();
        Long targetFolderId = faqTransferReq.getTargetFolderId();
        Long targetFileId = faqTransferReq.getTargetFileId();

        //获取知识库
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        String primitiveName = knowledgeBase.getPrimitiveName();
        Set<String> labels = getLabels(kbId, targetFileId, targetFolderId);

        Integer pageNo = 1;
        Integer pageSize = 500;

        FaqQueryReq faqQueryReq = FaqQueryReq.builder()
                .primitiveName(primitiveName)
                .faqType(FaqTypeEnums.SOURCE_FAQ.getCode())
                .pageSize(pageNo)
                .isNeedFolderId(false)
                .pageSize(pageSize)
                .build();

        //文件夹
        if (!CollectionUtils.isEmpty(folderIds)) {
            faqQueryReq.setFolderIds(folderIds);
            Page<FaqInfo> faqPage = chunnkDomainService.pageFaqList(faqQueryReq);
            List<FaqInfo> records = faqPage.getRecords();
            while (true) {
                updateFaqs(primitiveName, records, labels, targetFolderId, targetFileId);
                if (records.size() < pageSize)
                    break;
                faqQueryReq.setPageNo(faqQueryReq.getPageNo() + 1);
            }
            faqQueryReq.setPageNo(1);
        }

        //文件
        if (!CollectionUtils.isEmpty(fileIds)) {
            faqQueryReq.setFolderIds(fileIds);
            faqQueryReq.setFaqFileIds(fileIds);
            Page<FaqInfo> faqPage = chunnkDomainService.pageFaqList(faqQueryReq);
            List<FaqInfo> records = faqPage.getRecords();
            while (true) {
                updateFaqs(primitiveName, records, labels, targetFolderId, targetFileId);
                if (records.size() < pageSize)
                    break;
                faqQueryReq.setPageNo(faqQueryReq.getPageNo() + 1);
            }
            faqQueryReq.setPageNo(1);
        }

        //FAQ主键
        if (!CollectionUtils.isEmpty(relatedpks)) {
            faqQueryReq.setFolderIds(null);
            faqQueryReq.setFaqFileIds(null);
            faqQueryReq.setRelatedPks(relatedpks);
            Page<FaqInfo> faqPage = chunnkDomainService.pageFaqList(faqQueryReq);
            List<FaqInfo> records = faqPage.getRecords();
            while (true) {
                updateFaqs(primitiveName, records, labels, targetFolderId, targetFileId);
                if (records.size() < pageSize)
                    break;
                faqQueryReq.setPageNo(faqQueryReq.getPageNo() + 1);
            }
        }

        return true;
    }

    private void updateFaqs(String primitiveName, List<FaqInfo> faqList, Set<String> labels, Long targetFolderId, Long targetFileId) {
        if (CollectionUtils.isEmpty(faqList))
            return;
        //修改FAQ标签
        if (Objects.isNull(targetFolderId))
            targetFolderId = targetFileId;
        List<FaqUpdateReq> updateList = Lists.newArrayList();
        Long finalTargetFolderId = targetFolderId;
        faqList.forEach(faqInfo -> {
            FaqUpdateReq faq = BeanUtil.copyProperties(faqInfo, FaqUpdateReq.class);
            faq.setSource(faqInfo.getSourceFile());
            faq.setKnowledgeBaseName(primitiveName);
            faq.setLabels(labels);
            faq.setFolderId(finalTargetFolderId);
            updateList.add(faq);
        });
        chunnkDomainService.updateFaqBatch(primitiveName, updateList);
    }

    private Set<String> getLabels(Long kbId, Long targetFileId, Long targetFolderId) {
        Set<String> labels;
        if (!Objects.isNull(targetFolderId) && Objects.isNull(targetFileId)) {
            //查询目标文件夹的标签
            List<Long> targetFolderIds = Lists.newArrayList();
            targetFolderIds.add(targetFileId);
            folderInfoDomainService.getParentFolderIds(Arrays.asList(targetFolderId), targetFolderIds);
            List<BizLabelDTO> bizLabelDTOS = bizLabelAppService.findByTargetIds(targetFolderIds);
            labels = bizLabelDTOS.stream().map(BizLabelDTO::getLabel).collect(Collectors.toSet());
        } else if (Objects.isNull(targetFolderId) && !Objects.isNull(targetFileId)) {
            //查询目标文件的标签
            labels = bizLabelAppService.findByFileId(kbId, targetFileId);
        } else
            throw new ApplicationException(ErrCodeEnum.FAQ_PARAM_ERROR);
        return labels;
    }

    @Override
    public Boolean deleteByPks(FaqDeleteReq faqDeleteReq) {
        List<Long> pks = faqDeleteReq.getPks();
        Long kbId = faqDeleteReq.getKbId();
        if (CollectionUtils.isEmpty(pks))
            return false;
        //获取知识库
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        String primitiveName = knowledgeBase.getPrimitiveName();
        chunnkDomainService.deleteFaqByPks(primitiveName, pks);
        return true;
    }
}
