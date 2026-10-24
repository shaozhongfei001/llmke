package com.gientech.ragindexservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.plugins.pagination.PageDTO;
import com.gientech.ragcommon.auth.enums.BizTypeEnums;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.constant.IndexConstant;
import com.gientech.ragcommon.index.dto.FolderDTO;
import com.gientech.ragcommon.index.dto.FolderInfoDTO;
import com.gientech.ragcommon.index.dto.SaveFolderInfoReq;
import com.gientech.ragcommon.index.enmus.*;
import com.gientech.ragcommon.index.request.*;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragindexservice.application.remote.PyEsClient;
import com.gientech.ragindexservice.application.remote.PyMilvusClient;
import com.gientech.ragindexservice.application.service.BizLabelAppService;
import com.gientech.ragindexservice.application.service.FolderInfoAppService;
import com.gientech.ragindexservice.domain.entity.FaqEsInfo;
import com.gientech.ragindexservice.domain.entity.FolderInfo;
import com.gientech.ragindexservice.domain.entity.KnowledgeBase;
import com.gientech.ragindexservice.domain.entity.KnowledgeBaseList;
import com.gientech.ragindexservice.domain.service.*;
import com.gientech.ragcommon.index.dto.BizLabelDTO;
import com.gientech.ragcommon.index.request.SaveBizLabelReq;
import com.gientech.start.storage.properties.StorageProperties;
import com.google.common.collect.Lists;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;

import java.util.*;
import java.util.stream.Collectors;

import static com.gientech.ragcommon.index.enmus.FileFieldEnums.FAQ_TABLE_NAME_PREFIX;

@Slf4j
@Service
public class FolderInfoAppServiceImpl implements FolderInfoAppService {

    @Autowired
    private FolderInfoDomainService folderInfoDomainService;

    @Autowired
    private KnowledgeBaseListDomainService knowledgeBaseListDomainService;

    @Autowired
    private KnowledgeBaseDomainService knowledgeBaseDomainService;

    @Autowired
    private ChunnkDomainService chunnkDomainService;

    @Autowired
    private StorageProperties storageProperties;

    @Autowired
    private GraphDomainService graphDomainService;

    @Autowired
    private BizLabelAppService bizLabelAppService;

    @Autowired
    private PyEsClient pyEsClient;

    @Autowired
    private PyMilvusClient pyMilvusClient;

    @Override
    public FolderInfoDTO findById(Long id) {
        if (Objects.isNull(id))
            return null;
        FolderInfo byId = folderInfoDomainService.findById(id);
        return BeanUtil.copyProperties(byId, FolderInfoDTO.class);
    }

    @Override
    public Boolean save(SaveFolderInfoReq folderInfoReq) {
        if (Objects.isNull(folderInfoReq))
            return false;
        Long kbId = folderInfoReq.getKbId();
        Long parentId = folderInfoReq.getParentId();
        String name = folderInfoReq.getName();
        Integer type = folderInfoReq.getType();
        FolderInfo existedFolderInfo = folderInfoDomainService.find(kbId, name, parentId, type);
        if (!Objects.isNull(existedFolderInfo))
            throw new ApplicationException(ErrCodeEnum.FOLER_NAME_SAME_ERROR);
        FolderInfo folderInfo = BeanUtil.copyProperties(folderInfoReq, FolderInfo.class);
        folderInfoDomainService.save(folderInfo);
        //保存标签
        saveSuperiorFolderLabel(folderInfo.getId());
        return Boolean.TRUE;
    }

    private void saveSuperiorFolderLabel(Long folderId) {
        List<String> superiorLabel = bizLabelAppService.findSuperiorLabel(BizTypeEnums.FOLDER, folderId);
        SaveBizLabelReq saveBizLabelReq = new SaveBizLabelReq();
        saveBizLabelReq.setLabel(superiorLabel);
        saveBizLabelReq.setBizType(BizTypeEnums.FOLDER.getCode());
        saveBizLabelReq.setTargetId(folderId);
        bizLabelAppService.save(saveBizLabelReq);
    }

    @Override
    public Boolean rename(UpdateFolderInfoReq folderInfoReq) {
        if (Objects.isNull(folderInfoReq))
            return false;
        Long folderId = folderInfoReq.getId();
        Long parentId = folderInfoReq.getParentId();
        String name = folderInfoReq.getName();
        Long kbId = folderInfoReq.getKbId();
        Integer type = folderInfoReq.getType();
        FolderInfo folderInfo = folderInfoDomainService.find(kbId, name, parentId, type);
        if (Objects.nonNull(folderInfo) && folderInfo.getId().equals(folderId))
            return true;
        if (Objects.nonNull(folderInfo) && !folderInfo.getId().equals(folderId))
            throw new ApplicationException(ErrCodeEnum.FOLER_NAME_SAME_ERROR);
        folderInfoDomainService.updateById(BeanUtil.copyProperties(folderInfoReq, FolderInfo.class));

//        if (FolderTypeEnums.FAQ_EXTRACT.getCode().equals(type) || FolderTypeEnums.FAQ_MANAGEMENT.getCode().equals(type))
//            updateFileSourceIdToNull(folderInfoReq);

        return true;
    }

    @Override
    public Page<FolderInfoDTO> list(Long pageNo, Long pageSize) {
        pageNo = Objects.isNull(pageNo) ? 1 : pageNo;
        pageSize = Objects.isNull(pageSize) ? 10 : pageSize;
        Page<FolderInfo> page = folderInfoDomainService.list(pageNo, pageSize);
        Page<FolderInfoDTO> result = new PageDTO<>();
        BeanUtil.copyProperties(page, result);
        result.setRecords(BeanUtil.copyToList(page.getRecords(), FolderInfoDTO.class));
        return result;
    }

    @Override
    public Boolean deleteById(Long id) {
        if (Objects.isNull(id))
            return false;
        //删除当前文件夹以及子文件夹
        List<Long> folderIds = Lists.newArrayList(id);
        folderInfoDomainService.getChildrenFolderIds(Lists.newArrayList(id), folderIds);
        folderInfoDomainService.deleteByIds(folderIds);

        //删除文件夹下的子文件
        List<KnowledgeBaseList> kbFiles = knowledgeBaseListDomainService.findByFolderIds(folderIds, null);
        if (CollectionUtils.isEmpty(kbFiles))
            return true;
        Long kbId = kbFiles.get(0).getKbId();
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);

        //删除文件
        knowledgeBaseListDomainService.deleteByIds(kbFiles.stream().map(KnowledgeBaseList::getId).toList());
        //删除文件相关的数据
        kbFiles.forEach(kbFile -> {
            if (knowledgeBaseListDomainService.deleteById(kbFile.getId()) > 0)
                deleteFile(kbFile, knowledgeBase.getPrimitiveName());
        });
        return true;
    }

    private Boolean deleteFile(KnowledgeBaseList knowledgeBaseFile, String primitiveName) {
        Integer parseType = knowledgeBaseFile.getParseType();
        String filePath = knowledgeBaseFile.getConvertedFilePath();
        String fileType = knowledgeBaseFile.getFileName().substring(knowledgeBaseFile.getFileName().lastIndexOf(".") + 1);
        if (IndexConstant.FILE_TYPE_LIST.contains(fileType))
            filePath = knowledgeBaseFile.getFilePath();
        List<String> filePaths = Lists.newArrayList();
        if(StringUtils.hasText(filePath))
            filePaths = Arrays.asList(filePath.replace(storageProperties.getDefaultStorageProperties().getEndPoint() + "/", ""));

        //删除文本块相关的数据
        if (
                (KbFileStatusEnums.PARSE_SUCCESS.getValue().equals(knowledgeBaseFile.getStatus()) && (ParseTypeEnums.FILE_PARSE.getCode().equals(parseType) || ParseTypeEnums.FAQ_FILE_PARSE.getCode().equals(parseType)))
                        || GraphParseStatusEnums.PARSE_SUCCESS.getValue().equals(knowledgeBaseFile.getGraphParseStatus())
        ) {
            //删除表
            chunnkDomainService.delFiles(primitiveName, filePaths);
            //删除table_summary_(摘要表)
            chunnkDomainService.delFiles(FileFieldEnums.TABLE_SUMMARY_PREFIX + primitiveName, filePaths);
            //删除 table_chunks_(chunk数据)
            chunnkDomainService.delFiles(FileFieldEnums.TABLE_CHUNKS_PREFIX + primitiveName, filePaths);
        }

        //删除faq数据
//        if (FaqExtractStatusEnums.EXTRACT_SUCCESS.getValue().equals(knowledgeBaseFile.getFaqExtractStatus())
//                && (ParseTypeEnums.FAQ_PARSE.getCode().equals(parseType) || ParseTypeEnums.FAQ_FILE_PARSE.getCode().equals(parseType))
//        ) {
//            //删除FAQ数据
//            chunnkDomainService.deleteFaq(primitiveName, Arrays.asList(knowledgeBaseFile.getId()), null);
//        }

        //删除图相关的数据
        if (GraphParseStatusEnums.PARSE_SUCCESS.getValue().equals(knowledgeBaseFile.getGraphParseStatus())) {
            //删除图空间下某个文件对应的点和边的数据
            graphDomainService.delGraphSpace(primitiveName, knowledgeBaseFile.getId());
            //milvus中图实体表删除
            String fileName = filePath.substring(filePath.lastIndexOf("/") + 1);
            graphDomainService.delGraphEntity(primitiveName, Arrays.asList(String.valueOf(knowledgeBaseFile.getId())), Arrays.asList(fileName));
        }

        //删除FAQ抽取的文件和FAQ管理的文件关联
//        Long fileId = knowledgeBaseFile.getId();
//        KnowledgeBaseList faqFile = knowledgeBaseListDomainService.findBySourceId(fileId);
//        knowledgeBaseListDomainService.updateSourceIdToNull(Objects.isNull(faqFile) ? null : Arrays.asList(faqFile.getId()));

        return true;
    }

    private void getFolderIds(List<Long> folderIds, List<Long> resultFolderIds) {
        if (!CollectionUtils.isEmpty(folderIds)) {
            List<FolderInfo> folderInfos = folderInfoDomainService.findByParentIds(folderIds);
            if (!CollectionUtils.isEmpty(folderInfos)) {
                List<Long> ids = folderInfos.stream().map(FolderInfo::getId).collect(Collectors.toList());
                resultFolderIds.addAll(ids);
                getFolderIds(ids, resultFolderIds);
            }
        }
    }

    @Override
    public Boolean fileTransfer(FileTransferReq fileTransferReq) {
        Long fileId = fileTransferReq.getFileId();
        Long targetFolderId = fileTransferReq.getTargetFolderId();
        KnowledgeBaseList kbFile = knowledgeBaseListDomainService.findById(fileId);
        if (Objects.isNull(kbFile))
            throw new ApplicationException(ErrCodeEnum.KB_FILE_NOT_EXISTS_ERROR);
        KnowledgeBaseList knowledgeBaseList = new KnowledgeBaseList();
        knowledgeBaseList.setId(fileId);
        knowledgeBaseList.setFolderId(targetFolderId);
        knowledgeBaseListDomainService.update(knowledgeBaseList);
        return true;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Boolean transfer(TransferReq transferReq) {
        Long targetId = transferReq.getTargetId();
        Long targetFolderId = transferReq.getTargetFolderId();
        switch (transferReq.getBizType()) {
            case FAQ_EXTRACT_FOLDER -> {
                transferFolder(targetId, targetFolderId);
            }
            case FOLDER, FAQ_FOLDER -> {
                transferFolder(targetId, targetFolderId);
                //继承标签
                extendsLabels(transferReq.getBizType(), transferReq.getTargetId(), transferReq.getKbName());
            }
            case KNOWLEDGE_BASE_FILE -> {
                transferFile(targetId, targetFolderId);
                //继承标签
                extendsLabels(transferReq.getBizType(), transferReq.getTargetId(), transferReq.getKbName());
            }
            case FAQ_EXTRACT_FILE -> {
                transferFile(targetId, targetFolderId);
            }
            case FAQ_FILE -> {
                //转移文件
                transferFile(targetId, targetFolderId);

                //继承标签
                extendsLabels(transferReq.getBizType(), transferReq.getTargetId(), transferReq.getKbName());
                //如果是转移到文件，则删除原文件
                transferFaqsOfFile(transferReq.getKbName(), targetFolderId, targetId);

            }
            case FAQ -> {
                chunnkDomainService.transferFaqBatch(transferReq.getKbName(), List.of(String.valueOf(transferReq.getTargetId())), targetFolderId);
                //继承标签
                extendsLabels(transferReq.getBizType(), transferReq.getTargetId(), transferReq.getKbName());
            }
        }

        return Boolean.TRUE;
    }

    private void transferFolder(Long targetId, Long targetFolderId) {
        FolderInfo folderInfo = folderInfoDomainService.findById(targetId);
        if (Objects.isNull(folderInfo))
            throw new ApplicationException(ErrCodeEnum.FOLDER_NOT_EXISTS_ERROR);
        folderInfoDomainService.transferFolder(folderInfo.getId(), targetFolderId);
    }

    private void transferFaqsOfFile(String kbName, Long targetFolderId, Long targetId) {
        if (Objects.nonNull(targetFolderId) && Objects.isNull(folderInfoDomainService.findById(targetFolderId))) {
            String indexName = FAQ_TABLE_NAME_PREFIX + kbName;
            List<FaqEsInfo.FaqEsMetadata> faqs = chunnkDomainService.findFaqsByFolderIds(indexName, "\"" + targetId + "\"");
            //转移faq
            List<String> pks = faqs.stream().map(FaqEsInfo.FaqEsMetadata::getPk).toList();
            chunnkDomainService.transferFaqBatch(kbName, pks, targetFolderId);
            knowledgeBaseListDomainService.deleteById(targetId);
        }
    }

    private void transferFile(Long targetId, Long targetFolderId) {
        KnowledgeBaseList kbFile = knowledgeBaseListDomainService.findById(targetId);
        if (Objects.isNull(kbFile))
            throw new ApplicationException(ErrCodeEnum.KB_FILE_NOT_EXISTS_ERROR);
        knowledgeBaseListDomainService.transferFile(kbFile.getId(), targetFolderId);
    }

    private void extendsLabels(BizTypeEnums bizType, Long targetId, String kbName) {
        Set<BizLabelDTO> all = bizLabelAppService.findAll(bizType, targetId, kbName);
        SaveBizLabelReq saveBizLabelReq = SaveBizLabelReq.builder().targetId(targetId)
                .bizType(bizType.getCode())
                .label(all.stream().map(BizLabelDTO::getLabel).toList())
                .kbName(kbName).build();
        bizLabelAppService.save(saveBizLabelReq);
    }

    private void batchTransfer(BizTypeEnums bizType, List<Long> targetIds, Long targetFolderId, String kbName) {
        switch (bizType) {
            case FAQ_EXTRACT_FOLDER -> {
                folderInfoDomainService.transferFolderBatch(targetIds, targetFolderId);
            }
            case FOLDER, FAQ_FOLDER -> {
                folderInfoDomainService.transferFolderBatch(targetIds, targetFolderId);
                //继承标签
                targetIds.forEach(targetId -> {
                    extendsLabels(bizType, targetId, kbName);
                });
            }
            case KNOWLEDGE_BASE_FILE -> {
                knowledgeBaseListDomainService.transferFileBatch(targetIds, targetFolderId);
                //继承标签
                targetIds.forEach(targetId -> {
                    extendsLabels(bizType, targetId, kbName);
                });
            }
            case FAQ_EXTRACT_FILE -> {
                knowledgeBaseListDomainService.transferFileBatch(targetIds, targetFolderId);
            }
            case FAQ_FILE -> {
                knowledgeBaseListDomainService.transferFileBatch(targetIds, targetFolderId);
                //继承标签
                targetIds.forEach(targetId -> {
                    extendsLabels(bizType, targetId, kbName);
                    transferFaqsOfFile(kbName, targetFolderId, targetId);
                });
            }
            case FAQ -> {
                List<String> idStrList = targetIds.stream().map(String::valueOf).toList();
                chunnkDomainService.transferFaqBatch(kbName, idStrList, targetFolderId);
                targetIds.forEach(targetId -> {
                    extendsLabels(bizType, targetId, kbName);
                });
            }
        }
    }


    @Override
    @Transactional(rollbackFor = Exception.class)
    public Boolean transferBatch(TransferBatchReq transferBatchReq) {
        //可能多种类型混合传
        if (CollectionUtils.isEmpty(transferBatchReq.getTarget())) {
            throw new ApplicationException(ErrCodeEnum.PARAM_IS_NULL);
        }
        List<Long> folderIds = transferBatchReq.getTarget().stream()
                .filter(target -> BizTypeEnums.isFolderType(target.getBizType().getCode()))
                .map(TransferBatchReq.TransferTarget::getTargetId).toList();
        List<Long> fileIds = transferBatchReq.getTarget().stream()
                .filter(target -> BizTypeEnums.isFileType(target.getBizType().getCode()))
                .map(TransferBatchReq.TransferTarget::getTargetId).toList();
        List<Long> faqIds = transferBatchReq.getTarget().stream()
                .filter(target -> BizTypeEnums.isFaq(target.getBizType().getCode()))
                .map(TransferBatchReq.TransferTarget::getTargetId).toList();
        Set<BizTypeEnums> types = transferBatchReq.getTarget().stream().map(TransferBatchReq.TransferTarget::getBizType).collect(Collectors.toSet());

        String kbName = transferBatchReq.getTarget().get(0).getKbName();
        for (BizTypeEnums type : types) {
            if (BizTypeEnums.isFolderType(type.getCode())) {
                batchTransfer(type, folderIds, transferBatchReq.getTargetFolderId(), kbName);
            }
            if (BizTypeEnums.isFileType(type.getCode())) {
                batchTransfer(type, fileIds, transferBatchReq.getTargetFolderId(), kbName);
            }
            if (BizTypeEnums.isFaq(type.getCode())) {
                batchTransfer(type, faqIds, transferBatchReq.getTargetFolderId(), kbName);
            }
        }
        transferBatchReq.getTarget().stream().filter(t -> !BizTypeEnums.isFAQExtract(t.getBizType())).forEach(target -> extendsLabels(target.getBizType(), target.getTargetId(), target.getKbName()));
        return Boolean.TRUE;
    }


    @Override
    public List<FolderInfoDTO> leveList(List<Long> kbIds) {
        List<FolderInfo> folderInfos = folderInfoDomainService.leveList(kbIds);
        if (CollectionUtils.isEmpty(folderInfos))
            return Lists.newArrayList();
        //第一层级的文件
        List<FolderInfoDTO> folderInfoDTOS = BeanUtil.copyToList(folderInfos, FolderInfoDTO.class);
        List<FolderInfoDTO> firstLeveFolers =
                folderInfoDTOS.stream().filter(folderInfo -> Objects.isNull(folderInfo.getParentId())).collect(Collectors.toList());
        firstLeveFolers.forEach(folder -> getSubFolders(folder, folderInfoDTOS));
        return firstLeveFolers;
    }

    private void getSubFolders(FolderInfoDTO folder, List<FolderInfoDTO> folderInfos) {
        Long pid = folder.getId();
        Iterator<FolderInfoDTO> iterator = folderInfos.iterator();
        while (iterator.hasNext()) {
            FolderInfoDTO oneFolder = iterator.next();
            Long parentId = oneFolder.getParentId();
            if (!Objects.isNull(parentId)) {
                if (pid.equals(parentId)) {
                    folder.getSubFolders().add(oneFolder);
                    getSubFolders(oneFolder, folderInfos);
                }
            }
        }
    }

    @Override
    public Boolean addLabel(Long folderId, String label) {
        FolderInfo folderInfo = folderInfoDomainService.findById(folderId);
        if (Objects.isNull(folderInfo))
            throw new ApplicationException(ErrCodeEnum.FOLDER_NOT_EXISTS_ERROR);
        //查询文件件以及子文件夹
        List<Long> folderIds = Lists.newArrayList(folderId);
        getFolderIds(Collections.singletonList(folderId), folderIds);
        //查询文件
        List<KnowledgeBaseList> kbFiles = knowledgeBaseListDomainService.findByFolderIds(folderIds, null);
        if (CollectionUtils.isEmpty(kbFiles))
            return false;
        //更新标签
        folderInfo.setFolderLabel(label);
        folderInfoDomainService.updateById(folderInfo);
        knowledgeBaseListDomainService.updateLabels(kbFiles.stream().map(KnowledgeBaseList::getId).collect(Collectors.toList()), label);
        return true;
    }

    @Override
    public String queryCreator(Long id) {
        return folderInfoDomainService.queryCreator(id);
    }


    @Override
    public List<FolderInfoDTO> recursiveFolderByKb(QueryFolderReq queryFolderReq) {
        return BeanUtil.copyToList(folderInfoDomainService.recursiveFolderByKb(queryFolderReq), FolderInfoDTO.class);
    }

    @Override
    public List<FolderDTO> folderFileList(QueryFolderReq queryFolderReq) {
        Integer type = queryFolderReq.getType();
        Long kbId = queryFolderReq.getKbId();
        List<FolderDTO> folderDTOS = Lists.newArrayList();
        //查询第一级的文件夹
        List<FolderInfo> fistFolders = folderInfoDomainService.folderList(kbId, type, null);
        //查询所有文件
        List<KnowledgeBaseList> kbFileList = knowledgeBaseListDomainService.findFileByKbId(kbId, ParseTypeEnums.FAQ_MANAGEMENT.getCode());
        //查询子文件夹
        List<FolderInfo> childrenFolders = folderInfoDomainService.folderList(kbId, FolderTypeEnums.FAQ_MANAGEMENT.getCode());
        //构建树状结构
        bulidFolder(kbId, folderDTOS, fistFolders, childrenFolders, kbFileList);
        return folderDTOS;
    }

    private void bulidFolder(Long kbId, List<FolderDTO> resultFolders, List<FolderInfo> fistFolders, List<FolderInfo> childrenFolders, List<KnowledgeBaseList> kbFileList) {

        //没有文件夹的文件
        kbFileList.forEach(file -> {
            Long folderId = file.getFolderId();
            if (Objects.isNull(folderId)) {
                FolderDTO kbFile = new FolderDTO();
                kbFile.setName(file.getFileName());
                kbFile.setFileId(file.getId());
                kbFile.setKbId(kbId);
                kbFile.setDataType(FaqListDataTypeEnums.FILE.getCode());
                resultFolders.add(kbFile);
            }
        });

        fistFolders.forEach(folder -> {
            FolderDTO folderDTO = new FolderDTO();
            folderDTO.setName(folder.getName());
            folderDTO.setFolderId(folder.getId());
            folderDTO.setKbId(kbId);
            resultFolders.add(folderDTO);

            //文件
            kbFileList.forEach(file -> {
                Long folderId = file.getFolderId();
                if (folder.getId().equals(folderId)) {
                    FolderDTO kbFile = new FolderDTO();
                    kbFile.setName(file.getFileName());
                    kbFile.setFolderId(folderId);
                    kbFile.setFileId(file.getId());
                    kbFile.setKbId(kbId);
                    kbFile.setDataType(FaqListDataTypeEnums.FILE.getCode());
                    folderDTO.getSubs().add(kbFile);
                }
            });

            //文件夹
            Long folderPid = folder.getId();
            childrenFolders.forEach(childrenFolder -> {
                if (folderPid.equals(childrenFolder.getParentId())) {
                    FolderDTO subFolder = new FolderDTO();
                    subFolder.setName(childrenFolder.getName());
                    subFolder.setFolderId(childrenFolder.getId());
                    subFolder.setKbId(kbId);
                    folderDTO.getSubs().add(subFolder);
                    bulidFolderTree(kbId, subFolder, childrenFolders, kbFileList);
                }
            });
        });
    }

    private void bulidFolderTree(Long kbId, FolderDTO folderDTO, List<FolderInfo> childrenFolders, List<KnowledgeBaseList> kbFileList) {
        if (!Objects.isNull(folderDTO)) {

            //文件
            kbFileList.forEach(file -> {
                Long folderId = file.getFolderId();
                if (!Objects.isNull(folderId) && folderId.equals(folderDTO.getFolderId())) {
                    FolderDTO subFile = new FolderDTO();
                    subFile.setName(file.getFileName());
                    subFile.setFileId(file.getId());
                    subFile.setKbId(kbId);
                    subFile.setFolderId(folderId);
                    subFile.setDataType(FaqListDataTypeEnums.FILE.getCode());
                    folderDTO.getSubs().add(subFile);
                }
            });


            //文件夹
            Long folderPid = folderDTO.getFolderId();
            childrenFolders.forEach(childrenFolder -> {
                if (folderPid.equals(childrenFolder.getParentId())) {
                    FolderDTO subFolder = new FolderDTO();
                    subFolder.setName(childrenFolder.getName());
                    subFolder.setFolderId(childrenFolder.getId());
                    subFolder.setKbId(kbId);
                    folderDTO.getSubs().add(subFolder);
                    bulidFolderTree(kbId, subFolder, childrenFolders, kbFileList);
                }
            });
        }
    }
}
