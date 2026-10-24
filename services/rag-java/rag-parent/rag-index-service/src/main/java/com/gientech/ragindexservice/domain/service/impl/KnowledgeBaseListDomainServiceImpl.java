package com.gientech.ragindexservice.domain.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.auth.dto.UserInfoDTO;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.dto.FileChunkDTO;
import com.gientech.ragcommon.index.dto.FileMetadataChunkDTO;
import com.gientech.ragcommon.index.dto.KnowledgeBaseFileDTO;
import com.gientech.ragcommon.index.enmus.FileListTypeEnums;
import com.gientech.ragcommon.index.enmus.KbFileStatusEnums;
import com.gientech.ragcommon.index.enmus.UploadFileTypeEnums;
import com.gientech.ragcommon.index.request.FolderAndFilerReq;
import com.gientech.ragcommon.index.request.KnowledgeBaseFileQueryReq;
import com.gientech.ragcommon.index.request.UploadFileListReq;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragcommon.infrastructure.exception.DomainException;
import com.gientech.ragindexservice.application.remote.UserClient;
import com.gientech.ragindexservice.domain.entity.*;
import com.gientech.ragindexservice.domain.repository.KnowledgeBaseListRepository;
import com.gientech.ragindexservice.domain.service.ChunnkDomainService;
import com.gientech.ragindexservice.domain.service.KnowledgeBaseDomainService;
import com.gientech.ragindexservice.domain.service.KnowledgeBaseListDomainService;
import com.google.common.collect.Sets;
import org.apache.commons.compress.utils.Lists;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;

import java.util.*;
import java.util.regex.Pattern;
import java.util.stream.Collectors;


/**
 * <p>
 * 知识库明细 服务实现类
 * </p>
 *
 * @author wudf
 * @since 2024-08-02
 */
@Service
public class KnowledgeBaseListDomainServiceImpl implements KnowledgeBaseListDomainService {

    @Autowired
    private KnowledgeBaseListRepository knowledgeBaseListRepository;

    @Autowired
    private KnowledgeBaseDomainService knowledgeBaseDomainService;

    @Autowired
    private ChunnkDomainService chunnkDomainService;

    @Autowired
    private UserClient userClient;

    static final String fileNameRegularChar = "[`~!@#$%^&*()_\\-+\\[\\]=<>?:\"{}|,\\/;'\\\\·~！@#￥%……&*（）.——\\-+={}|〔〕《》？：“”【】、；‘'，。、]|(pdf|png|jpeg|jpg|docx|xlsx|pjpg|svg|csv|txt)$";

    private static final String fileNameRegularDigit = "\\d+";

    private static final String fileNameRegular = "\\【[^\\【\\】]*\\】|\\[[^\\[\\]]*\\]|\\([^\\(\\)]*\\)|（[^（）]*）|[`~!@#$%^&*()_\\-+\\[\\]=<>?:\"{}|,\\/;'\\\\·~！@#￥%……&*（）.——\\-+={}|〔〕《》？：“”【】、；‘'，。、]|\\s|\\d|(pdf|png|jpeg|jpg|docx|xlsx|pjpg|svg|csv|txt)$";

    @Override
    public List<KnowledgeBaseList> insertBatch(List<KnowledgeBaseList> knowledgeBaseLists) {
        return knowledgeBaseListRepository.insertBatch(knowledgeBaseLists);
    }

    @Override
    public void updateStatusByFilePaths(List<String> filePaths, Integer status) {
        knowledgeBaseListRepository.updateStatusByFilePaths(filePaths, status);
    }

    @Override
    public void updateLabels(List<Long> fileIds, String label) {
        knowledgeBaseListRepository.updateLabels(fileIds, label);
    }

    @Override
    public void updateStatusByIds(List<Long> ids, Integer status, boolean convertedFilePathSetNull) {
        knowledgeBaseListRepository.updateStatusByIds(ids, status, convertedFilePathSetNull);
    }

    @Override
    public Page<KnowledgeBaseList> list(Long kbId, Integer fileListType, String fuzzy, Integer status, Integer faqExtractStatus, String parentFileName, Long pageNo, Long pageSize) {
        return knowledgeBaseListRepository.list(kbId, fileListType, fuzzy, status, faqExtractStatus, parentFileName, pageNo, pageSize);
    }

    @Override
    public void updateParseStatusByIds(List<Long> fileIds, Integer status, Boolean needUpdateTime) {
        knowledgeBaseListRepository.updateParseStatusByIds(fileIds, status, needUpdateTime);
    }

    @Override
    public void updateGraphExtractByIds(List<Long> graphExtractFileIds, Integer graphExtractStatus) {
        knowledgeBaseListRepository.updateGraphExtractByIds(graphExtractFileIds, graphExtractStatus);
    }

    @Override
    public int deleteById(Long id) {
        KnowledgeBaseList knowledgeBaseList = new KnowledgeBaseList();
        knowledgeBaseList.setId(id);
        knowledgeBaseList.setStatus(KbFileStatusEnums.DELETE.getValue());
        return knowledgeBaseListRepository.updateById(knowledgeBaseList);
    }

    @Override
    public List<KnowledgeBaseList> findFileByKbId(Long kbId) {
        return knowledgeBaseListRepository.findFileByKbId(kbId);
    }

    @Override
    public List<KnowledgeBaseList> findFileByKbId(Long kbId, List<Integer> parseTypes) {
        return knowledgeBaseListRepository.findFileByKbId(kbId, parseTypes);
    }

    @Override
    public KnowledgeBaseList findFileByKbIdAndFileName(Long kbId, String fileName) {
        return knowledgeBaseListRepository.findFileByKbIdAndFileName(kbId, fileName);
    }

    @Override
    public KnowledgeBaseList findFileByKbIdAndNameFuzzy(Long kbId, String fileNameFuzzy) {
        return knowledgeBaseListRepository.findFileByKbIdAndNameFuzzy(kbId, fileNameFuzzy);
    }

    @Override
    public List<KnowledgeBaseList> findFileByKbIdAndFileStatus(Long kbId, List<Integer> parseStatus, List<Integer> extractStatus) {
        return knowledgeBaseListRepository.findFileByKbIdAndFileStatus(kbId, parseStatus, extractStatus);
    }

    @Override
    public Map<Long, KnowledgeBaseFile> findFileInfo(List<Long> kbIds) {
        return knowledgeBaseListRepository.findFileInfo(kbIds);
    }

    @Override
    public KnowledgeBaseList findById(Long id) {
        return knowledgeBaseListRepository.findById(id);
    }

    @Override
    public List<KnowledgeBaseList> findByIds(Long[] ids) {
        return knowledgeBaseListRepository.findByIds(Arrays.asList(ids));
    }

    @Override
    public Boolean updateEnable(List<Long> fileIds, Integer enableStatus) {
        return knowledgeBaseListRepository.updateEnable(fileIds, enableStatus);
    }

    @Override
    public List<KnowledgeBaseList> findByIds(List<Long> fileIds) {
        return knowledgeBaseListRepository.findByIds(fileIds);
    }

    @Override
    public KnowledgeBaseList update(KnowledgeBaseList knowledgeBaseList) {
        knowledgeBaseListRepository.updateById(knowledgeBaseList);
        return knowledgeBaseList;
    }

    @Override
    public boolean deleteByIds(List<Long> ids) {
        return knowledgeBaseListRepository.deleteByIds(ids);
    }

    @Override
    public void updateExtractStatusByFilePaths(List<String> filePaths, Integer extractStatus) {
        knowledgeBaseListRepository.updateExtractStatusByFilePaths(filePaths, extractStatus);
    }

    @Override
    public void updateExtractStatusByIds(List<Long> ids, Integer extractStatus) {
        knowledgeBaseListRepository.updateExtractStatusByIds(ids, extractStatus);
    }

    @Override
    public boolean checkFileName(List<UploadFileListReq.UploadFile> fileList) {
        if (CollectionUtils.isEmpty(fileList))
            throw new DomainException(ErrCodeEnum.FILE_LIST_EMPTY_ERROR);
        List<UploadFileListReq.UploadFile> files = fileList.stream().filter(file -> Objects.isNull(file.getType())).collect(Collectors.toList());
        if (CollectionUtils.isEmpty(files))
            return false;
        Set<String> fileNames = files.stream().map(file -> file.getFileName()).collect(Collectors.toSet());
        return fileList.size() > fileNames.size();
    }

    @Override
    public Set<String> checkFileNameForDb(Long kbId, Integer fileListType, List<UploadFileListReq.UploadFile> fileList) {
        if (CollectionUtils.isEmpty(fileList))
            return Sets.newHashSet();

        List<UploadFileListReq.UploadFile> files = fileList.stream().filter(file -> Objects.isNull(file.getType())).collect(Collectors.toList());
        if (CollectionUtils.isEmpty(files))
            return Sets.newHashSet();

        List<KnowledgeBaseList> kbFiles = knowledgeBaseListRepository.findFileByKbIdAndType(kbId, fileListType);
        if (CollectionUtils.isEmpty(kbFiles))
            return Sets.newHashSet();

        Set<String> fileNames = files.stream().map(file -> file.getFileName()).collect(Collectors.toSet());
        Set<String> dbFileNames = kbFiles.stream().map(file -> file.getFileName()).collect(Collectors.toSet());
        fileNames.retainAll(dbFileNames);
        return fileNames;
    }

    @Override
    public List<KbFile> recognise(UploadFileListReq uploadFileList) {
        List<UploadFileListReq.UploadFile> fileList = uploadFileList.getFileList();
        Integer fileListType = uploadFileList.getFileListType();
        Long kbId = uploadFileList.getKbId();
        Boolean isParse = uploadFileList.getIsParse();
        Boolean isExtract = uploadFileList.getIsExtract();

        if (CollectionUtils.isEmpty(fileList))
            return Lists.newArrayList();

        if (FileListTypeEnums.FILE_LIST.getCode().equals(fileListType)) {
            if (isExtract && !isParse)
                fileListType = FileListTypeEnums.FAQ_LIST.getCode();
            else if (isExtract && isParse)
                fileListType = null;
        }

        List<KbFile> kbFileList = Lists.newArrayList();
        //查询最新版本(父文件名维度)
        List<KnowledgeBaseList> kbFiles = knowledgeBaseListRepository.findFileMaxVersion(kbId, fileListType);
        Map<String, KnowledgeBaseList> kbFileMap = convertToMap(kbFiles);
//        Pattern pattern = Pattern.compile(fileNameRegularDigit);
        fileList.forEach(uploadFile -> {
            String fileName = uploadFile.getFileName();
            String fileNamePrefix = fileName.substring(0, fileName.indexOf("."));
            String fileNameSuffix = fileName.substring(fileName.indexOf(".") + 1);
            UploadFileTypeEnums type = uploadFile.getType();
            String uid = uploadFile.getUid();
//            String parentFileName = getparentFileName(fileName,pattern);
            KnowledgeBaseList dbKbFile = kbFileMap.get(fileName);
            KbFile kbFile = BeanUtil.copyProperties(uploadFileList, KbFile.class);
            kbFile.setParentFileName(fileName);
//            kbFile.setGroupId((fileName.hashCode() & Integer.MAX_VALUE) + "");
            kbFile.setFileName(fileName);
            kbFile.setMultipartFile(uploadFile.getMultipartFile());
            kbFile.setFolderId(uploadFileList.getFolderId());
            kbFile.setSourceUrl(uploadFile.getSourceUrl());
            kbFile.setUid(uid);
            String version = "V0";
            Integer v = 0;
            //版本号
            if (UploadFileTypeEnums.NEWVERSION.equals(type)) {
                if (!Objects.isNull(dbKbFile)) {
                    version = dbKbFile.getVersion();
                    v = Integer.parseInt(version.replace("V", "")) + 1;
                    version = "V" + v;
//                    kbFile.setIsMultipleVersion(true);
                    kbFile.setVersion(version);
                    kbFile.setFileName(fileNamePrefix + "(" + v + ")" + "." + fileNameSuffix);
                }
                kbFileList.add(kbFile);
            } else if (UploadFileTypeEnums.OVERWRITE.equals(type)) {
                if (!Objects.isNull(dbKbFile)) {
                    version = dbKbFile.getVersion();
                    v = Integer.parseInt(version.replace("V", ""));
//                    kbFile.setIsMultipleVersion(v > 0);
                }
                kbFile.setVersion(version);
                kbFile.setFileName(v.equals(0) ? fileName : (fileNamePrefix + "(" + v + ")" + "." + fileNameSuffix));
                kbFileList.add(kbFile);
            } else if (UploadFileTypeEnums.SKIP.equals(type)) {
                //不处理
            } else if (Objects.isNull(type)) {
                kbFile.setVersion(version);
                kbFileList.add(kbFile);
            }
            kbFile.setGroupId((kbFile.getFileName().hashCode() & Integer.MAX_VALUE) + "");
        });

        return kbFileList;
    }

    @Override
    public KbFile recogniseCompressedFile(UploadFileListReq.UploadFile uploadFile, UploadFileListReq uploadFileReq, String entryName, String rawFileName, Map<String, Long> folderInfoMap, List<KnowledgeBaseList> kbFiles) {
        Map<String, KnowledgeBaseList> kbFileMap = convertToMap(kbFiles);
        Pattern pattern = Pattern.compile(fileNameRegularDigit);
        String fileNamePrefix = rawFileName.substring(0, rawFileName.indexOf("."));
        String fileNameSuffix = rawFileName.substring(rawFileName.indexOf(".") + 1);
        UploadFileTypeEnums type = uploadFile.getType();
        if (Objects.isNull(type))
            type = uploadFile.getType();
        String parentFileName = getparentFileName(rawFileName, pattern);
        KnowledgeBaseList dbKbFile = kbFileMap.get(parentFileName);
        KbFile kbFile = BeanUtil.copyProperties(uploadFileReq, KbFile.class);
        kbFile.setParentFileName(parentFileName);
        kbFile.setFileName(rawFileName);
        kbFile.setGroupId((kbFile.getFileName().hashCode() & Integer.MAX_VALUE) + "");
        kbFile.setSourceUrl(uploadFile.getSourceUrl());
        Long folderId = null;
        String folder = entryName.substring(0, entryName.lastIndexOf(rawFileName));
        if (!StringUtils.hasText(folder)) {
            folderId = uploadFileReq.getFolderId();
        } else {
            folderId = folderInfoMap.get(folder);
        }
        kbFile.setFolderId(folderId);
        String version = "V0";
        Integer v = 0;
        //版本号
        if (UploadFileTypeEnums.NEWVERSION.equals(type)) {
            if (!Objects.isNull(dbKbFile)) {
                version = dbKbFile.getVersion();
                v = Integer.parseInt(version.replace("V", "")) + 1;
                version = "V" + v;
//                    kbFile.setIsMultipleVersion(true);
            }
            kbFile.setVersion(version);
            kbFile.setFileName(fileNamePrefix + "(" + v + ")" + "." + fileNameSuffix);

        } else if (UploadFileTypeEnums.OVERWRITE.equals(type)) {
            if (!Objects.isNull(dbKbFile)) {
                version = dbKbFile.getVersion();
                v = Integer.parseInt(version.replace("V", ""));
//                    kbFile.setIsMultipleVersion(v > 0);
            }
            kbFile.setVersion(version);
            kbFile.setFileName(v.equals(0) ? rawFileName : (fileNamePrefix + "(" + v + ")" + "." + fileNameSuffix));

        } else if (UploadFileTypeEnums.SKIP.equals(type)) {
            //不处理
            kbFile = null;
        } else if (Objects.isNull(type)) {
            kbFile.setVersion(version);

        }
        return kbFile;
    }

    private String getparentFileName(String fileName, Pattern pattern) {
        String parentFileName = "";
        String fileNameStr = fileName.replaceAll(fileNameRegularChar, "");
        if (StringUtils.hasText(fileNameStr) && pattern.matcher(fileNameStr).matches())
            parentFileName = fileNameStr;
        else
            parentFileName = fileName.replaceAll(fileNameRegular, "");
        return parentFileName;
    }

    private Map<String, KnowledgeBaseList> convertToMap(List<KnowledgeBaseList> kbFiles) {
        Map<String, KnowledgeBaseList> kbFileMap = new HashMap<>();
        if (CollectionUtils.isEmpty(kbFiles))
            return kbFileMap;
        kbFiles.forEach(kbFile -> kbFileMap.put(kbFile.getParentFileName(), kbFile));
        return kbFileMap;
    }

    @Override
    public Page<KnowledgeBaseList> parentList(Long kbId, Integer fileListType, String fuzzy, Integer status, Integer faqExtractStatus, Integer showType, List<Long> kbIds, Long pageNo, Long pageSize) {
        return knowledgeBaseListRepository.parentList(kbId, fileListType, fuzzy, status, faqExtractStatus, showType, kbIds, pageNo, pageSize);
    }

    @Override
    public List<KnowledgeBaseList> findFileByKbIdAndType(Long kbId, Integer fileListType) {
        return knowledgeBaseListRepository.findFileByKbIdAndType(kbId, fileListType);
    }

    @Override
    public List<KnowledgeBaseList> findFileMaxVersion(Long kbId, Integer fileListType) {
        return knowledgeBaseListRepository.findFileMaxVersion(kbId, fileListType);
    }

    @Override
    public List<KnowledgeBaseList> findByFolderId(Long folderId) {
        return knowledgeBaseListRepository.findByFolderId(folderId);
    }

    @Override
    public List<KnowledgeBaseList> recursiveByFolderId(Long folderId) {
        return knowledgeBaseListRepository.recursiveByFolderId(folderId);
    }

    @Override
    public Page<KbFileExt> folderList(Long kbId, Integer fileListType, List<Integer> statusList, Integer faqExtractStatus, String fuzzy, Long folderId, Long pageNo, Long pageSize) {
        return knowledgeBaseListRepository.folderList(kbId, fileListType, statusList, faqExtractStatus, fuzzy, folderId, pageNo, pageSize);
    }

    @Override
    public LinkedHashSet<KbFileExt> fileList(Set<Long> kbIds, Integer status, String kbName, Set<Long> folderIds, String userName, boolean withFolder) {
        LinkedHashSet<KbFileExt> kbFileExts = knowledgeBaseListRepository.fileList(kbIds, status, kbName, folderIds, userName, withFolder);
        return Objects.nonNull(kbFileExts) ? kbFileExts : new LinkedHashSet<>();
    }

    @Override
    public Page<KbFileExt> onlyFileList(KnowledgeBaseFileQueryReq req) {
        Page<KbFileExt> page = new Page<>();
        page.setCurrent(req.getPageNo());
        page.setSize(req.getPageSize());
        return knowledgeBaseListRepository.onlyFileList(page, req.getKbIds(), req.getStatus(), req.getKbName(), req.getFolderIds(), req.getUserName());
    }


    @Override
    public List<KbFileExt> onlyFileListByTime(KnowledgeBaseFileQueryReq req) {
        return knowledgeBaseListRepository.onlyFileListByTime(req.getKbIds(), req.getKbName(), req.getFolderIds(), req.getUserName(), req.getStartTime(), req.getEndTime(), req.getStatusArray());
    }


    @Override
    public List<KnowledgeBaseList> findByFolderIds(List<Long> folderIds, List<Integer> status) {
        return knowledgeBaseListRepository.findByFolderIds(folderIds, status);
    }

    @Override
    public List<KnowledgeBaseList> findByFolderIds(List<Long> folderIds, List<Integer> parseStatus, List<Integer> faqExtractStatus, List<Integer> graphParseStatus) {
        return knowledgeBaseListRepository.findByFolderIds(folderIds, parseStatus, faqExtractStatus, graphParseStatus);
    }

    @Override
    public List<KnowledgeBaseList> findFileByFolder(List<Long> folderIds) {
        return knowledgeBaseListRepository.findFileByFolder(folderIds);
    }

    @Override
    public List<KnowledgeBaseList> findNoParseFiles(Long kbId, List<Integer> parseTypes) {
        return knowledgeBaseListRepository.findNoParseFiles(kbId, parseTypes);
    }

    @Override
    public List<KnowledgeBaseList> findNoExtractFiles(Long kbId, List<Integer> parseTypes) {
        return knowledgeBaseListRepository.findNoExtractFiles(kbId, parseTypes);
    }

    @Override
    public String getParentFileName(String fileName) {
        Pattern pattern = Pattern.compile(fileNameRegularDigit);
        return getparentFileName(fileName, pattern);
    }

    @Override
    public String getVersionByParentFileName(Long kbId, String parentFileName) {
        String version = "V0";
        Integer v = 0;
        KnowledgeBaseList dbKbFile = knowledgeBaseListRepository.findByParentFileName(kbId, parentFileName);
        if (dbKbFile != null) {
            version = dbKbFile.getVersion();
            v = Integer.parseInt(version.replace("V", "")) + 1;
            version = "V" + v;
        }
        return version;
    }

    @Override
    public List<KnowledgeBaseList> queryList(Long kbId, List<Integer> types) {
        return knowledgeBaseListRepository.queryList(kbId, types);
    }

    @Override
    public List<KnowledgeBaseList> getByKbIdAndUid(Long kbId, List<String> fileUids, Integer tempStatus) {
        return knowledgeBaseListRepository.getByKbIdAndUid(kbId, fileUids, tempStatus);
    }

    @Override
    public List<KnowledgeBaseList> findByUids(List<String> uids) {
        return knowledgeBaseListRepository.findByUids(uids);
    }

    @Override
    public KnowledgeBaseFileDTO findFile(Long kbId, String fileName, Integer type) {
        return knowledgeBaseListRepository.findFile(kbId, fileName, type);
    }

    @Override
    public Boolean updateTempStatusByUid(List<String> fileUids, Integer temStatus) {
        return knowledgeBaseListRepository.updateTempStatusByUid(fileUids, temStatus);
    }

    @Override
    public Boolean updateMultiversion(List<Long> fileIds, String parentFileName, String groupId, String versionDate) {
        return knowledgeBaseListRepository.updateMultiversion(fileIds, parentFileName, groupId, versionDate);
    }

    @Override
    public KnowledgeBaseList findByKbIdAndGroupIds(Long kbId, String groupId) {
        return knowledgeBaseListRepository.findByKbIdAndGroupId(kbId, groupId);
    }

    @Override
    public List<KnowledgeBaseList> findByKbIdAndGroupIds(Long kbId, List<String> groupIds, List<Integer> parseTypes) {
        return knowledgeBaseListRepository.findByKbIdAndGroupIds(kbId, groupIds, parseTypes);
    }

    @Override
    public List<KnowledgeBaseList> findByKbId(Long kbId, List<Integer> parseTypes, List<Long> excludeFolderIds, List<Long> excludeFileIds, List<Integer> parseStatus, List<Integer> faqExtractStatus) {
        return knowledgeBaseListRepository.findByKbId(kbId, parseTypes, excludeFolderIds, excludeFileIds, parseStatus, faqExtractStatus);
    }

    @Override
    public List<KnowledgeBaseList> scatterList(Long kbId, Integer fileListType) {
        return knowledgeBaseListRepository.scatterList(kbId, fileListType);
    }

    @Override
    public KnowledgeBaseList findFileGroup(Long kbId, String groupId, List<Integer> parseTypes) {
        return knowledgeBaseListRepository.findFileGroup(kbId, groupId, parseTypes);
    }

    @Override
    public List<KnowledgeBaseList> findFileByKbId(Long kbId, Integer parseType) {
        return knowledgeBaseListRepository.findFileByKbId(kbId, parseType);
    }

    @Override
    public List<KnowledgeBaseList> collectList(Long kbId, Integer parseType) {
        return knowledgeBaseListRepository.collectList(kbId, parseType);
    }

    @Override
    public List<KnowledgeBaseList> findByKbIdAndGroupIds(Long kbId, List<String> groupIds) {
        return knowledgeBaseListRepository.findByKbIdAndGroupIds(kbId, groupIds);
    }

    @Override
    public List<KnowledgeBaseList> queryListWithPermission(Long kbId) {
        UserInfoDTO user = userClient.getUserInfo();
        return knowledgeBaseListRepository.queryListWithPermission(kbId, user.getLongTypeDeptId(), user.getId());
    }

    @Override
    public List<KnowledgeBaseList> queryListWithPermission(Long kbId, Integer folderType, Integer parseType, List<Integer> bizTypes) {
        UserInfoDTO user = userClient.getUserInfo();
        return knowledgeBaseListRepository.queryListWithPermission(kbId, user.getLongTypeDeptId(), user.getId(), folderType, parseType, bizTypes);
    }

    @Override
    public List<KnowledgeBaseList> queryNoPermissionFiles(Long kbId) {
        UserInfoDTO user = userClient.getUserInfo();
        return knowledgeBaseListRepository.queryNoPermissionFiles(kbId, user.getLongTypeDeptId(), user.getId());

    }

    @Override
    public String queryCreator(Long id) {
        KnowledgeBaseList knowledgeBaseList = knowledgeBaseListRepository.findById(id);
        return Objects.isNull(knowledgeBaseList) ? null : knowledgeBaseList.getCreateBy();
    }

    @Override
    public void transferFile(Long id, Long folderId) {
        knowledgeBaseListRepository.transferFile(id, folderId);
    }


    @Override
    public void transferFileBatch(List<Long> ids, Long folderId) {
        knowledgeBaseListRepository.transferFileBatch(ids, folderId);
    }

    @Override
    public Page<KbFileExt> folderAndFileList(FolderAndFilerReq params, Integer pageNo, Integer pageSize) {
        return knowledgeBaseListRepository.folderAndFileList(params, pageNo, pageSize);
    }

    @Override
    public List<KnowledgeBaseList> findByFolderId(Long kbId, Integer type, Long folerId) {
        return knowledgeBaseListRepository.findByFolderId(kbId, type, folerId);
    }

    @Override
    public List<KnowledgeBaseList> findFileByFilePaths(Long kbId, List<String> filePaths, Integer type) {
        return knowledgeBaseListRepository.findFileByFilePaths(kbId, filePaths, type);
    }


    @Override
    public List<FileChunkDTO> getFileChunks(Long docId, Integer pageNo, Integer pageSize) {
        return buildFileChunkDTO(getChunks(docId, pageNo, pageSize));
    }


    @Override
    public List<FileMetadataChunkDTO> getFileMetadataChunks(Long docId, Integer pageNo, Integer pageSize) {
        return buildFileMetadataChunkDTO(getChunks(docId, pageNo, pageSize));
    }

    @Override
    public JSONObject getChunks(Long docId, Integer pageNo, Integer pageSize) {
        KnowledgeBaseList knowledgeBaseFile = knowledgeBaseListRepository.findById(docId);
        if (Objects.isNull(knowledgeBaseFile)) throw new ApplicationException(ErrCodeEnum.KB_FILE_NOT_EXISTS_ERROR);
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(knowledgeBaseFile.getKbId());
        if (Objects.isNull(knowledgeBase)) throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        String primitiveName = knowledgeBase.getPrimitiveName();
        String fileName = knowledgeBaseFile.getFileName();
        return chunnkDomainService.getChunks(primitiveName, fileName, pageNo, pageSize);
    }

    @Override
    public Long getSequenceCodeByFileId(Long fileId) {
        return knowledgeBaseListRepository.getSequenceCodeByFileId(fileId);
    }

    private List<FileChunkDTO> buildFileChunkDTO(JSONObject respJson) {
        if (Objects.isNull(respJson))
            return com.google.common.collect.Lists.newArrayList();
        JSONObject data = respJson.getJSONObject("data");
        List<FileChunkDTO> chunks = com.google.common.collect.Lists.newArrayList();
        if (Objects.isNull(data)) {
            return chunks;
        }
        JSONArray resultData = data.getJSONArray("result_data");
        if (Objects.isNull(resultData)) {
            return chunks;
        }
        resultData.forEach(result -> {
            FileChunkDTO fileChunkDTO = new FileChunkDTO();
            Long chunkId = ((JSONObject) result).getLong("_id");
            String tableName = ((JSONObject) result).getString("_index");
            JSONObject dataJson = ((JSONObject) result).getJSONObject("_source");
            String chunkContent = dataJson.getString("page_content");
            JSONObject chunkMetadataJson = dataJson.getJSONObject("metadata");
            fileChunkDTO.setPicChunkIdList(JSON.parseArray(chunkMetadataJson.getString("pic_children_id_list"), Long.class));
            fileChunkDTO.setPicUrlList(JSON.parseArray(chunkMetadataJson.getString("pic_url_list"), String.class));
            fileChunkDTO.setImagePath(chunkMetadataJson.getString("image_path"));
            fileChunkDTO.setPageNumbers(chunkMetadataJson.getJSONArray("page_number"));
            fileChunkDTO.setPositions(chunkMetadataJson.getJSONArray("position"));
            fileChunkDTO.setPageSizes(chunkMetadataJson.getJSONArray("page_size"));
            fileChunkDTO.setOffsets(chunkMetadataJson.getJSONArray("offset"));
            fileChunkDTO.setTable(chunkMetadataJson.getString("table_name"));
            fileChunkDTO.setType(chunkMetadataJson.getString("type"));
            fileChunkDTO.setTableName(tableName);
            if (org.apache.commons.lang3.StringUtils.isNotBlank(chunkContent)) {
                fileChunkDTO.setId(chunkId);
                fileChunkDTO.setContent(chunkContent);
                chunks.add(fileChunkDTO);
            }
        });
        return chunks;
    }

    private List<FileMetadataChunkDTO> buildFileMetadataChunkDTO(JSONObject respJson) {
        if (Objects.isNull(respJson))
            return com.google.common.collect.Lists.newArrayList();
        JSONObject data = respJson.getJSONObject("data");
        List<FileMetadataChunkDTO> chunks = Lists.newArrayList();
        if (Objects.isNull(data)) {
            return chunks;
        }
        JSONArray resultData = data.getJSONArray("result_data");
        if (Objects.isNull(resultData)) {
            return chunks;
        }
        resultData.forEach(result -> {
            JSONObject dataJson = ((JSONObject) result).getJSONObject("_source");
            FileMetadataChunkDTO metadata = dataJson.getObject("metadata", FileMetadataChunkDTO.class);
            chunks.add(metadata);
        });
        return chunks;
    }
}
