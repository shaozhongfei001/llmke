package com.gientech.ragindexservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.alibaba.excel.util.StringUtils;
import com.alibaba.fastjson.JSON;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.plugins.pagination.PageDTO;
import com.gientech.ragcommon.auth.enums.BizTypeEnums;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.enmus.FolderTypeEnums;
import com.gientech.ragcommon.index.request.PyLabelReq;
import com.gientech.ragcommon.index.response.PyEsResponse;
import com.gientech.ragcommon.index.response.PyMilvusResponse;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragindexservice.application.remote.PyEsClient;
import com.gientech.ragindexservice.application.remote.PyMilvusClient;
import com.gientech.ragindexservice.application.service.BizLabelAppService;
import com.gientech.ragindexservice.domain.entity.BizLabel;
import com.gientech.ragindexservice.domain.entity.FaqEsInfo;
import com.gientech.ragindexservice.domain.entity.FolderInfo;
import com.gientech.ragindexservice.domain.entity.KnowledgeBaseList;
import com.gientech.ragindexservice.domain.service.BizLabelDomainService;
import com.gientech.ragindexservice.domain.service.ChunnkDomainService;
import com.gientech.ragindexservice.domain.service.FolderInfoDomainService;
import com.gientech.ragindexservice.domain.service.KnowledgeBaseListDomainService;
import com.gientech.ragcommon.index.dto.BizLabelDTO;
import com.gientech.ragcommon.index.request.SaveBizLabelReq;
import com.gientech.ragcommon.index.request.UpdateBizLabelReq;
import com.google.common.collect.Maps;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.compress.utils.Lists;
import org.assertj.core.util.Sets;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.CollectionUtils;

import java.util.*;
import java.util.stream.Collectors;

import static com.gientech.ragcommon.index.enmus.FileFieldEnums.FAQ_TABLE_NAME_PREFIX;

@Service
@Slf4j
public class BizLabelAppServiceImpl implements BizLabelAppService {

    private final BizLabelDomainService bizLabelDomainService;

    private final FolderInfoDomainService folderInfoDomainService;

    private final KnowledgeBaseListDomainService knowledgeBaseListDomainService;

    private final PyMilvusClient pyMilvusClient;

    private final ChunnkDomainService chunnkDomainService;

    private final PyEsClient pyEsClient;

    public BizLabelAppServiceImpl(BizLabelDomainService bizLabelDomainService,
                                  FolderInfoDomainService folderInfoDomainService,
                                  KnowledgeBaseListDomainService knowledgeBaseListDomainService,
                                  PyMilvusClient pyMilvusClient,
                                  PyEsClient pyEsClient, ChunnkDomainService chunnkDomainService
    ) {
        this.bizLabelDomainService = bizLabelDomainService;
        this.folderInfoDomainService = folderInfoDomainService;
        this.knowledgeBaseListDomainService = knowledgeBaseListDomainService;
        this.pyMilvusClient = pyMilvusClient;
        this.pyEsClient = pyEsClient;
        this.chunnkDomainService = chunnkDomainService;
    }

    @Override
    public BizLabelDTO findById(Long id) {
        if (Objects.isNull(id))
            return null;
        BizLabel byId = bizLabelDomainService.findById(id);
        return BeanUtil.copyProperties(byId, BizLabelDTO.class);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Boolean save(SaveBizLabelReq bizLabelReq) {
        if (Objects.isNull(bizLabelReq))
            return false;
        List<BizLabel> labels = bizLabelReq.getLabel().stream()
                .filter(StringUtils::isNotBlank)
                .map(s -> BizLabel.builder().label(s.trim()).bizType(bizLabelReq.getBizType()).targetId(bizLabelReq.getTargetId()).build()).toList();


        //组装请求算法端的参数
        BizTypeEnums bizType = Objects.requireNonNull(BizTypeEnums.of(bizLabelReq.getBizType()));
        PyLabelReq pyLabelReq = buildPyLabelReq(bizLabelReq, bizType, labels);
        String pyLabelReqJSONString = pyLabelReq.getJSONString(bizType);
        if (!CollectionUtils.isEmpty(pyLabelReq.getFileIds()) || !CollectionUtils.isEmpty(pyLabelReq.getPk())) {

            log.info("python client param:{}", pyLabelReqJSONString);

            updateEs(pyLabelReqJSONString);
            updateMilvus(pyLabelReqJSONString, pyLabelReq.isUseBatch());

        }

        if (CollectionUtils.isEmpty(labels)) {
            BizLabel bizLabel = BizLabel.builder().bizType(bizLabelReq.getBizType()).targetId(bizLabelReq.getTargetId()).build();
            bizLabelDomainService.deleteBatch(bizLabel);
        } else {
            bizLabelDomainService.saveBatch(labels);
        }


        return Boolean.TRUE;
    }

    private void updateEs(String request) {
        PyEsResponse<Object> esResponse = pyEsClient.updateById(request);
        if (!esResponse.getCode().equals(200)) {
            throw new ApplicationException(ErrCodeEnum.PY_ES_LABEL_ERROR);
        }
    }

    private void updateMilvus(String request, boolean isUseBatch) {
        PyMilvusResponse<Object> milvusResponse;
        if (isUseBatch) {
            milvusResponse = pyMilvusClient.updateByIdBatch(request);
        } else {
            milvusResponse = pyMilvusClient.updateById(request);
        }

        if (!milvusResponse.getCode().equals(200)) {
            throw new ApplicationException(ErrCodeEnum.PY_MILVUS_LABEL_ERROR);
        }
    }


    private PyLabelReq buildPyLabelReq(SaveBizLabelReq bizLabelReq, BizTypeEnums bizType, List<BizLabel> bizLabels) {
        PyLabelReq pyLabelReq = new PyLabelReq();
        pyLabelReq.setIndexName(bizLabelReq.getKbName());
        pyLabelReq.setColName("labels");
        Long targetId = bizLabelReq.getTargetId();
        Set<String> labels = bizLabels.stream().map(BizLabel::getLabel).collect(Collectors.toSet());

        Map<String, Map<String, Object>> labelMap = Maps.newHashMap();
        switch (bizType) {
            case KNOWLEDGE_BASE_FILE -> {
                //如果是知识库文件，则更新对应的知识库文件
                pyLabelReq.setColValue(labels);
                pyLabelReq.setFileIds(List.of(String.valueOf(targetId)));
            }
            case FOLDER -> {
                //如果是文件夹，则更新文件夹下的文件(文件要带上自己的label）
                //先查出文件夹的差集
                //再查出文件标签和文件夹差集的并集，再更新文件
                FolderInfo folderInfo = folderInfoDomainService.findById(targetId);
                if (Objects.isNull(folderInfo))
                    throw new ApplicationException(ErrCodeEnum.FOLDER_NOT_EXISTS_ERROR);
                List<KnowledgeBaseList> fileList = knowledgeBaseListDomainService.recursiveByFolderId(targetId);//带文件label
                List<String> fileIds = fileList.stream().map(i -> String.valueOf(i.getId())).toList();
                log.info("bizType:folder:fileIds:{}", JSON.toJSONString(fileIds));
                upgradeFileLabels(targetId, fileList, labels, labelMap, fileIds);

                pyLabelReq.setFileIds(fileIds);
                pyLabelReq.setUpdateFileName("file_id");
                pyLabelReq.setUpdateConditionJson(labelMap);
                pyLabelReq.setUseBatch(true);
            }
            case FAQ -> {
                //index_name改为faq前缀
                //fileId改成pk
                String indexName = pyLabelReq.getIndexName();
                pyLabelReq.setIndexName(FAQ_TABLE_NAME_PREFIX + indexName);
                pyLabelReq.setPk(List.of(String.valueOf(targetId)));

                FaqEsInfo.FaqEsMetadata faqEsMetadata = chunnkDomainService.findFaqByPk(indexName, targetId);
                if (Objects.isNull(faqEsMetadata)) {
                    throw new ApplicationException(ErrCodeEnum.FAQ_NOT_EXIST_ERROR);
                }
                pyLabelReq.setColValue(labels);

            }
            case FAQ_FOLDER, FAQ_FILE -> {
                //获取已有文件夹标签的和现在的差集
                List<String> existedFolderLabels = bizLabelDomainService.findLabelsByTargetIds(List.of(targetId));
                Set<String> diffLabels = difference(labels, existedFolderLabels);

                upgradeFaqFileLabels(targetId, labels, existedFolderLabels);

                //差集合并到faq的标签中,getFaqsByFolderId, label = label+diffLabels saveFaqs

                List<FaqEsInfo.FaqEsMetadata> faqs = chunnkDomainService.findFaqsByFolderIds(FAQ_TABLE_NAME_PREFIX + bizLabelReq.getKbName(), getSubFolderStrByFolderId(targetId));
                //更新文件夹
                //更新faq
                faqs.forEach(faq -> {
                    faq.getLabels().addAll(diffLabels);
                    labelMap.put(faq.getPk(), getLabelList(faq.getLabels()));
                });
                pyLabelReq.setUseBatch(true);
                pyLabelReq.setPk(faqs.stream().map(FaqEsInfo.FaqEsMetadata::getPk).collect(Collectors.toList()));
                pyLabelReq.setIndexName(FAQ_TABLE_NAME_PREFIX + bizLabelReq.getKbName());
                pyLabelReq.setUpdateConditionJson(labelMap);
            }
            default -> throw new IllegalArgumentException(ErrCodeEnum.BIZ_TYPE_NOT_EXIST.getErrMsg());
        }
        return pyLabelReq;

    }

    private String getSubFolderStrByFolderId(Long targetId) {
        Set<Long> subFolderIds = folderInfoDomainService.findSubFolderById(targetId).stream().map(FolderInfo::getId).collect(Collectors.toSet());
        return subFolderIds.stream().map(folderId -> "\"" + folderId + "\"").collect(Collectors.joining(","));
    }

    private Map<String, Object> getLabelList(Set<String> labels) {
        Map<String, Object> labelList = Maps.newHashMap();
        labelList.put("labels", labels);
        return labelList;
    }


    private void upgradeFileLabels(Long targetId, List<KnowledgeBaseList> fileList, Set<String> labels, Map<String, Map<String, Object>> labelMap, List<String> fileIds) {
        List<String> existedFolderLabels = bizLabelDomainService.findLabelsByTargetIds(List.of(targetId));
        List<BizLabel> fileListUpgradeLabels = Lists.newArrayList();
        for (KnowledgeBaseList file : fileList) {
            Set<String> fullLabelOfFile = getFullLabelOfFile(labels, file.getLabel(), existedFolderLabels);
            labelMap.put(String.valueOf(file.getId()), getLabelList(fullLabelOfFile));
            List<BizLabel> upgradeBizLabels = fullLabelOfFile.stream().map(label -> BizLabel.builder()
                    .bizType(getBizTypeOfFileOrFolder(file.getIsFolder()))
                    .label(label)
                    .targetId(file.getId())
                    .build()).toList();
            fileListUpgradeLabels.addAll(upgradeBizLabels);
        }
        if (!CollectionUtils.isEmpty(fileIds)) {
            bizLabelDomainService.saveBatch(fileListUpgradeLabels);
        }
    }

    private Integer getBizTypeOfFileOrFolder(Integer isFolder) {
        return isFolder.equals(1) ? BizTypeEnums.FOLDER.getCode() : BizTypeEnums.KNOWLEDGE_BASE_FILE.getCode();
    }

    /**
     * 更新faq文件、文件夹的标签
     *
     * @param targetId            文件/文件夹id
     * @param labels              传入的标签
     * @param existedFolderLabels 文件/文件夹id已存在的标签
     */
    private void upgradeFaqFileLabels(Long targetId, Set<String> labels, List<String> existedFolderLabels) {
        //更新文件夹下的文件和文件夹
        List<BizLabel> upgradeLabelList = Lists.newArrayList();
        List<KnowledgeBaseList> fileList = knowledgeBaseListDomainService.recursiveByFolderId(targetId);//带文件label
        fileList.forEach(file -> {
            Set<String> fullLabelOfFile = getFullLabelOfFile(labels, file.getLabel(), existedFolderLabels);
            List<BizLabel> bizLabelsOfFile = fullLabelOfFile.stream().map(label -> BizLabel.builder()
                    .targetId(file.getId())
                    .bizType(getBizTypeOfFaqFileOrFolder(file.getIsFolder()))
                    .label(label).build()).toList();
            upgradeLabelList.addAll(bizLabelsOfFile);
        });
        bizLabelDomainService.saveBatch(upgradeLabelList);
    }

    private Integer getBizTypeOfFaqFileOrFolder(Integer isFolder) {
        return isFolder.equals(1) ? BizTypeEnums.FAQ_FOLDER.getCode() : BizTypeEnums.FAQ_FILE.getCode();
    }


    private Set<String> getFullLabelOfFile(Set<String> folderLabel, String fileLabel, List<String> existedFolderLabels) {
        //计算folderLabel和existedFolderLabels的差集
        Set<String> difference = difference(folderLabel, existedFolderLabels);
        Set<String> fileLabels = Sets.newHashSet();
        if (StringUtils.isNotBlank(fileLabel)) {
            fileLabels = Arrays.stream(fileLabel.split(",")).map(String::trim)
                    .filter(s -> !s.isEmpty())      // 去除空字符串
                    .collect(Collectors.toSet());

        }
        fileLabels.addAll(difference);
        return fileLabels;
    }

    public Set<String> difference(Set<String> a, List<String> b) {
        Set<String> result = new HashSet<>(a);
        b.forEach(result::remove);
        return result;
    }

    @Override
    public Boolean updateById(UpdateBizLabelReq bizLabelReq) {
        if (Objects.isNull(bizLabelReq))
            return false;
        return bizLabelDomainService.updateById(BeanUtil.copyProperties(bizLabelReq, BizLabel.class));
    }

    @Override
    public Page<BizLabelDTO> list(Long pageNo, Long pageSize) {
        pageNo = Objects.isNull(pageNo) ? 1 : pageNo;
        pageSize = Objects.isNull(pageSize) ? 10 : pageSize;
        Page<BizLabel> page = bizLabelDomainService.list(pageNo, pageSize);
        Page<BizLabelDTO> result = new PageDTO<>();
        BeanUtil.copyProperties(page, result);
        result.setRecords(BeanUtil.copyToList(page.getRecords(), BizLabelDTO.class));
        return result;
    }

    @Override
    public Boolean deleteById(Long id) {
        if (Objects.isNull(id))
            return false;
        return bizLabelDomainService.deleteById(id);
    }


    @Override
    public Set<BizLabelDTO> findAll(BizTypeEnums bizTypeEnum, Long targetId, String indexName) {
        Set<BizLabel> bizLabels = new HashSet<>();
        switch (bizTypeEnum) {
            case FOLDER, FAQ_FOLDER -> {
                List<FolderInfo> folderInfos = folderInfoDomainService.findParentIdsById(targetId);
                if (!CollectionUtils.isEmpty(folderInfos)) {
                    bizLabels = new HashSet<>(bizLabelDomainService.findByTargetIds(getTargetIdsByFolderList(folderInfos)));
                }
            }
            case KNOWLEDGE_BASE_FILE, FAQ_FILE -> {
                KnowledgeBaseList knowledgeBaseFile = knowledgeBaseListDomainService.findById(targetId);
                if (Objects.isNull(knowledgeBaseFile)) {
                    return Set.of();
                }
                List<FolderInfo> folderInfos = folderInfoDomainService.findParentIdsById(knowledgeBaseFile.getFolderId());
                List<Long> targetIds = new ArrayList<>(folderInfos.stream().map(FolderInfo::getId).toList());
                targetIds.add(knowledgeBaseFile.getId());
                targetIds.add(knowledgeBaseFile.getFolderId());
                bizLabels = new HashSet<>(bizLabelDomainService.findByTargetIds(targetIds));
            }
            case FAQ -> {
                FaqEsInfo.FaqEsMetadata faq = chunnkDomainService.findFaqByPk(indexName, targetId);
                if (Objects.nonNull(faq)) {
                    if (StringUtils.isNotBlank(faq.getFolderId())) {
                        List<FolderInfo> folderInfos = folderInfoDomainService.findParentIdsById(Long.valueOf(faq.getFolderId()));
                        List<Long> targetIds = new ArrayList<>(folderInfos.stream().map(FolderInfo::getId).toList());
                        targetIds.add(Long.valueOf(faq.getFolderId()));
                        bizLabels = new HashSet<>(bizLabelDomainService.findByTargetIds(targetIds));
                        bizLabels.addAll(faq.getBizLabels());
                    } else {
                        bizLabels = faq.getBizLabels();
                    }
                }
            }
        }
        return new HashSet<>(BeanUtil.copyToList(bizLabels, BizLabelDTO.class));
    }


    @Override
    public List<BizLabelDTO> findByTargetIds(List<Long> targetIds) {
        List<BizLabel> bizLabels = bizLabelDomainService.findByTargetIds(targetIds);
        return BeanUtil.copyToList(bizLabels, BizLabelDTO.class);
    }

    private List<Long> getTargetIdsByFolderList(List<FolderInfo> folderInfos) {
        List<Long> targetIds = Lists.newArrayList();
        targetIds.addAll(folderInfos.stream().map(FolderInfo::getId).toList());
        targetIds.add(folderInfos.get(0).getKbId());
        return targetIds;
    }

    @Override
    public List<BizLabelDTO> findByKbNames(List<String> kbNames) {
        List<BizLabel> bizLabels = bizLabelDomainService.findByKbNames(kbNames);
        return BeanUtil.copyToList(bizLabels, BizLabelDTO.class);
    }

    @Override
    public List<BizLabelDTO> historyOfKbLabel(Long kbId) {
        List<BizLabel> historyOfKbLabel = bizLabelDomainService.findHistoryOfKbLabel(kbId);
        return BeanUtil.copyToList(historyOfKbLabel, BizLabelDTO.class);
    }

    /**
     * 获取继承的标签
     *
     * @param bizTypeEnums
     * @param targetId
     * @return
     */
    @Override
    public List<String> findSuperiorLabel(BizTypeEnums bizTypeEnums, Long targetId) {
        switch (bizTypeEnums) {
            case KNOWLEDGE_BASE_FILE -> {
                KnowledgeBaseList file = knowledgeBaseListDomainService.findById(targetId);
                Long folderId = file.getFolderId();
                Set<BizLabelDTO> folderLabels = findAll(BizTypeEnums.FOLDER, folderId, null);
                return folderLabels.stream().map(BizLabelDTO::getLabel).toList();
            }
            case FOLDER -> {
                Set<BizLabelDTO> folderLabels = findAll(bizTypeEnums, targetId, null);
                return folderLabels.stream().map(BizLabelDTO::getLabel).toList();
            }
        }
        return List.of();
    }

    @Override
    public Set<String> findByFileId(Long kbId, Long fileId) {
        if (Objects.isNull(kbId) || Objects.isNull(fileId))
            return Sets.newHashSet();
        KnowledgeBaseList kbFile = knowledgeBaseListDomainService.findById(fileId);
        if (Objects.isNull(kbFile))
            throw new ApplicationException(ErrCodeEnum.KB_FILE_NOT_EXISTS_ERROR);

        List<Long> targetIds = Lists.newArrayList();
        targetIds.add(fileId);
        Long folderId = kbFile.getFolderId();
        if (!Objects.isNull(folderId)) {
            FolderInfo folder = folderInfoDomainService.findById(folderId);
            String fullPath = folder.getFullPath();
            // 文件夹1/文件夹2/文件夹3/
            String folderName;
            String newFullPath = "";
            List<String> fullPaths = com.google.common.collect.Lists.newArrayList();
            while (fullPath.contains("/")) {
                folderName = fullPath.substring(0, fullPath.indexOf("/"));
                newFullPath = newFullPath + folderName + "/";
                fullPaths.add(newFullPath);
                fullPath = fullPath.substring(fullPath.indexOf("/") + 1);
            }
            //查询文件夹id
            List<FolderInfo> folderInfos = folderInfoDomainService.findByFullPaths(kbId, fullPaths, FolderTypeEnums.FAQ_MANAGEMENT.getCode());
            List<Long> folderIds = folderInfos.stream().map(FolderInfo::getId).collect(Collectors.toList());
            targetIds.addAll(folderIds);
        }
        List<BizLabelDTO> bizLabelDTOS = this.findByTargetIds(targetIds);
        return bizLabelDTOS.stream().map(BizLabelDTO::getLabel).collect(Collectors.toSet());
    }
}
