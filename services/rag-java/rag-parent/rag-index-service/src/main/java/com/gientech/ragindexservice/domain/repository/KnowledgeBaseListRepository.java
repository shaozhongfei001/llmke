package com.gientech.ragindexservice.domain.repository;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.IService;
import com.gientech.ragcommon.index.dto.KnowledgeBaseFileDTO;
import com.gientech.ragcommon.index.request.FolderAndFilerReq;
import com.gientech.ragindexservice.domain.entity.KbFileExt;
import com.gientech.ragindexservice.domain.entity.KnowledgeBaseFile;
import com.gientech.ragindexservice.domain.entity.KnowledgeBaseList;
import com.gientech.ragindexservice.domain.model.KnowledgeBaseListDO;

import java.time.LocalDateTime;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public interface KnowledgeBaseListRepository extends IService<KnowledgeBaseListDO> {
    List<KnowledgeBaseList> insertBatch(List<KnowledgeBaseList> knowledgeBaseLists);

    void updateStatusByFilePaths(List<String> filePaths, Integer status);

    void updateStatusByIds(List<Long> ids, Integer status, boolean convertedFilePathSetNull);

    Page<KnowledgeBaseList> list(Long kbId, Integer fileListType, String fuzzy, Integer status, Integer faqExtractStatus, String parentFileName, Long pageNo, Long pageSize);

    int updateById(KnowledgeBaseList knowledgeBaseList);

    List<KnowledgeBaseList> findFileByKbId(Long kbId);

    List<KnowledgeBaseList> recursiveByFolderId(Long folderId);

    List<KnowledgeBaseList> findFileByKbId(Long kbId, List<Integer> parseTypes);

    List<KnowledgeBaseList> findFileByKbId(Long kbId, Integer parseType);

    KnowledgeBaseList findFileByKbIdAndFileName(Long kbId, String fileName);

    Map<Long, KnowledgeBaseFile> findFileInfo(List<Long> kbIds);

    KnowledgeBaseList findById(Long id);

    Boolean updateEnable(List<Long> fileIds, Integer enableStatus);

    List<KnowledgeBaseList> findByIds(List<Long> fileIds);

    KnowledgeBaseList findFileByKbIdAndNameFuzzy(Long kbId, String fileNameFuzzy);

    List<KnowledgeBaseList> findFileByKbIdAndFileStatus(Long kbId, List<Integer> parseStatus, List<Integer> extractStatus);

    boolean deleteByIds(List<Long> ids);

    void updateExtractStatusByFilePaths(List<String> filePaths, Integer extractStatus);

    List<KnowledgeBaseList> findFileByKbIdAndType(Long kbId, Integer fileListType);

    List<KnowledgeBaseList> findFileMaxVersion(Long kbId, Integer fileListType);

    Page<KnowledgeBaseList> parentList(
            Long kbId, Integer fileListType, String fuzzy, Integer status, Integer faqExtractStatus, Integer showType,
            List<Long> kbIds,Long pageNo, Long pageSize);

    List<KnowledgeBaseList> findByFolderId(Long folderId);

    Page<KbFileExt> folderList(Long kbId, Integer fileListType, List<Integer> status, Integer faqExtractStatus, String fuzzy, Long folderId, Long pageNo, Long pageSize);

    Page<KbFileExt> folderAndFileList(FolderAndFilerReq params, Integer pageNo, Integer pageSize);

    LinkedHashSet<KbFileExt> fileList(Set<Long> kbIds, Integer status, String kbName, Set<Long> folderIds, String userName, boolean withFolder);

    Page<KbFileExt> onlyFileList(Page<KbFileExt> page, Set<Long> kbIds, Integer status, String kbName, Set<Long> folderIds, String userName);

    List<KbFileExt> onlyFileListByTime(Set<Long> kbIds, String kbName, Set<Long> folderIds, String userName, LocalDateTime startTime, LocalDateTime endTime, int[] statusArray);

    List<KnowledgeBaseList> findByFolderIds(List<Long> folderIds, List<Integer> status);

    List<KnowledgeBaseList> findByFolderIds(List<Long> folderIds,List<Integer> parseStatus, List<Integer> faqExtractStatus, List<Integer> graphParseStatus);

    void updateExtractStatusByIds(List<Long> ids, Integer extractStatus);

    List<KnowledgeBaseList> findNoParseFiles(Long kbId, List<Integer> parseTypes);

    List<KnowledgeBaseList> findNoExtractFiles(Long kbId, List<Integer> parseTypes);

    KnowledgeBaseList findByParentFileName(Long kbId, String parentFileName);

    List<KnowledgeBaseList> queryList(Long kbId, List<Integer> types);

    List<KnowledgeBaseList> getByKbIdAndUid(Long kbId, List<String> fileUids, Integer tempStatus);

    List<KnowledgeBaseList> findByUids(List<String> uids);

    KnowledgeBaseFileDTO findFile(Long kbId, String fileName, Integer type);

    Boolean updateTempStatusByUid(List<String> fileUids, Integer temStatus);

    Boolean updateMultiversion(List<Long> fileIds, String parentFileName, String groupId,String versionDate);

    List<KnowledgeBaseList> collectList(Long kbId, Integer fileListType);

    KnowledgeBaseList findByKbIdAndGroupId(Long kbId, String groupId);

    List<KnowledgeBaseList> findByKbIdAndGroupIds(Long kbId, List<String> groupIds, List<Integer> parseTypes);

    List<KnowledgeBaseList> findByKbId(Long kbId, List<Integer> parseTypes, List<Long> excludeFolderIds, List<Long> excludeFileIds, List<Integer> parseStatus, List<Integer> faqExtractStatus);

    List<KnowledgeBaseList> scatterList(Long kbId, Integer fileListType);

    KnowledgeBaseList findFileGroup(Long kbId, String groupId, List<Integer> parseTypes);

    List<KnowledgeBaseList> queryListWithPermission(Long kbId, Long deptId, Long userId);

    List<KnowledgeBaseList> queryListWithPermission(Long kbId, Long deptId, Long userId, Integer folderType, Integer parseType, List<Integer> bizTypes);

    List<KnowledgeBaseList> queryNoPermissionFiles(Long kbId, Long deptId, Long userId);

    List<KnowledgeBaseList> findByKbIdAndGroupIds(Long kbId, List<String> groupIds);

    void updateLabels(List<Long> fileIds, String label);

    void transferFile(Long id, Long folderId);

    void transferFileBatch(List<Long> ids, Long folderId);

    List<KnowledgeBaseList> findByFolderId(Long kbId, Integer type, Long folerId);

    List<KnowledgeBaseList> findFileByFolder(List<Long> folderIds);

    List<KnowledgeBaseList> findFileByFilePaths(Long kbId, List<String> filePaths, Integer type);

    Long getSequenceCodeByFileId(Long fileId);

    void updateParseStatusByIds(List<Long> fileIds, Integer status, Boolean needUpdateTime);

    void updateGraphExtractByIds(List<Long> graphExtractFileIds, Integer graphExtractStatus);
}
