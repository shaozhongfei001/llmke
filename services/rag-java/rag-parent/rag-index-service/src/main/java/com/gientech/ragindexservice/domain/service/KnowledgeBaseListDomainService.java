package com.gientech.ragindexservice.domain.service;

import com.alibaba.fastjson2.JSONObject;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.dto.FileChunkDTO;
import com.gientech.ragcommon.index.dto.FileMetadataChunkDTO;
import com.gientech.ragcommon.index.dto.KnowledgeBaseFileDTO;
import com.gientech.ragcommon.index.request.FolderAndFilerReq;
import com.gientech.ragcommon.index.request.KnowledgeBaseFileQueryReq;
import com.gientech.ragcommon.index.request.UploadFileListReq;
import com.gientech.ragindexservice.domain.entity.KbFile;
import com.gientech.ragindexservice.domain.entity.KbFileExt;
import com.gientech.ragindexservice.domain.entity.KnowledgeBaseFile;
import com.gientech.ragindexservice.domain.entity.KnowledgeBaseList;

import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * <p>
 * 知识库明细 服务类
 * </p>
 *
 * @author wudf
 * @since 2024-08-02
 */
public interface KnowledgeBaseListDomainService {

    List<KnowledgeBaseList> insertBatch(List<KnowledgeBaseList> knowledgeBaseLists);

    void updateStatusByFilePaths(List<String> filePaths, Integer status);

    void updateStatusByIds(List<Long> ids, Integer status, boolean convertedFilePathSetNull);

    Page<KnowledgeBaseList> list(Long kbId, Integer fileListType, String fuzzy, Integer status, Integer faqExtractStatus, String parentFileName, Long pageNo, Long pageSize);

    int deleteById(Long id);

    List<KnowledgeBaseList> findFileByKbId(Long kbId);

    List<KnowledgeBaseList> findFileByKbId(Long kbId, List<Integer> parseTypes);

    List<KnowledgeBaseList> findFileByKbId(Long kbId, Integer parseType);

    KnowledgeBaseList findFileByKbIdAndFileName(Long kbId, String fileName);

    KnowledgeBaseList findFileByKbIdAndNameFuzzy(Long kbId, String fileNameFuzzy);

    List<KnowledgeBaseList> findFileByKbIdAndFileStatus(Long kbId, List<Integer> parseStatus, List<Integer> extractStatus);

    Map<Long, KnowledgeBaseFile> findFileInfo(List<Long> kbIds);

    KnowledgeBaseList findById(Long id);

    List<KnowledgeBaseList> findByIds(Long[] ids);

    Boolean updateEnable(List<Long> fileIds, Integer enableStatus);

    List<KnowledgeBaseList> findByIds(List<Long> fileIds);

    KnowledgeBaseList update(KnowledgeBaseList knowledgeBaseList);

    boolean deleteByIds(List<Long> ids);

    void updateExtractStatusByFilePaths(List<String> filePaths, Integer extractStatus);

    void updateExtractStatusByIds(List<Long> ids, Integer extractStatus);

    /**
     * 判断文件名是否重复
     *
     * @param fileList
     * @return
     */
    boolean checkFileName(List<UploadFileListReq.UploadFile> fileList);

    /**
     * 判断文件名是否和数据库中的文件名重复
     *
     * @param kbId
     * @param fileListType
     * @param fileList
     * @return
     */
    Set<String> checkFileNameForDb(Long kbId, Integer fileListType, List<UploadFileListReq.UploadFile> fileList);

    /**
     * 版本识别(父文件名和文件版本号)
     *
     * @param uploadFileList
     * @return
     */
    List<KbFile> recognise(UploadFileListReq uploadFileList);

    /**
     * 版本识别(父文件名和文件版本号)
     *
     * @param uploadFile
     * @param uploadFileReq
     * @param entryName
     * @param rawFileName
     * @param kbFiles
     * @return
     */
    KbFile recogniseCompressedFile(UploadFileListReq.UploadFile uploadFile, UploadFileListReq uploadFileReq, String entryName, String rawFileName, Map<String, Long> folderInfoMap, List<KnowledgeBaseList> kbFiles);

    /**
     * 查询父文件
     *
     * @param kbId
     * @param fileListType
     * @param pageNo
     * @param pageSize
     * @return
     */
    Page<KnowledgeBaseList> parentList(Long kbId, Integer fileListType, String fuzzy, Integer status, Integer faqExtractStatus, Integer showType,List<Long> kbIds, Long pageNo, Long pageSize);

    List<KnowledgeBaseList> findFileByKbIdAndType(Long kbId, Integer fileListType);

    List<KnowledgeBaseList> findFileMaxVersion(Long kbId, Integer fileListType);

    List<KnowledgeBaseList> findByFolderId(Long folerId);

    List<KnowledgeBaseList> recursiveByFolderId(Long folderId);

    Page<KbFileExt> folderList(Long kbId, Integer fileListType, List<Integer> statusList, Integer faqExtractStatus, String fuzzy, Long folderId, Long pageNo, Long pageSize);

    LinkedHashSet<KbFileExt> fileList(Set<Long> kbIds, Integer status, String kbName, Set<Long> folderIds, String userName, boolean withFolder);

    Page<KbFileExt> onlyFileList(KnowledgeBaseFileQueryReq req);

    List<KbFileExt> onlyFileListByTime(KnowledgeBaseFileQueryReq req);

    List<KnowledgeBaseList> findByFolderIds(List<Long> folderIds, List<Integer> status);

    List<KnowledgeBaseList> findByFolderIds(List<Long> folderIds,List<Integer> parseStatus, List<Integer> faqExtractStatus, List<Integer> graphParseStatus);

    List<KnowledgeBaseList> findFileByFolder(List<Long> folderIds);

    List<KnowledgeBaseList> findNoParseFiles(Long kbId, List<Integer> parseTypes);

    List<KnowledgeBaseList> findNoExtractFiles(Long kbId, List<Integer> parseTypes);

    /**
     * 根据文件名获取父文件名
     *
     * @param fileName
     * @return
     */
    String getParentFileName(String fileName);

    /**
     * 根据父文件名获取版本号
     *
     * @param kbId
     * @param parentFileName
     * @return
     */
    String getVersionByParentFileName(Long kbId, String parentFileName);

    /**
     * 通过知识库id查询文档
     *
     * @param kbId
     * @param types
     * @return
     */
    List<KnowledgeBaseList> queryList(Long kbId, List<Integer> types);

    /**
     * 通过知识库名和文件fileuIds查询文件，fileUids如果是null，查询当前知识库下所有的文件
     *
     * @param kbId
     * @param fileUids
     * @return
     */
    List<KnowledgeBaseList> getByKbIdAndUid(Long kbId, List<String> fileUids, Integer tempStatus);

    /**
     * 通过uid查询数据
     *
     * @param uids
     * @return
     */
    List<KnowledgeBaseList> findByUids(List<String> uids);

    List<KnowledgeBaseList> findByKbIdAndGroupIds(Long kbId, List<String> groupIds);

    List<KnowledgeBaseList> queryListWithPermission(Long kbId);

    List<KnowledgeBaseList> queryListWithPermission(Long kbId, Integer folderType,Integer parseType, List<Integer> bizTypes);

    List<KnowledgeBaseList> queryNoPermissionFiles(Long kbId);

    String queryCreator(Long id);

    /**
     * 查询文件
     *
     * @param kbId
     * @param fileName
     * @param type
     * @return
     */
    KnowledgeBaseFileDTO findFile(Long kbId, String fileName, Integer type);

    /**
     * 持久化文件
     *
     * @param fileUids
     * @param temStatus
     * @return
     */
    Boolean updateTempStatusByUid(List<String> fileUids, Integer temStatus);

    /**
     * 通过知识库id和组id查询(返回一条记录)
     *
     * @param kbId
     * @param groupId
     * @return
     */
    KnowledgeBaseList findByKbIdAndGroupIds(Long kbId, String groupId);

    /**
     * 通过文件id更新符文件和文件集组id
     *
     * @param fileIds
     * @param parentFileName
     * @param groupId
     * @return
     */
    Boolean updateMultiversion(List<Long> fileIds, String parentFileName, String groupId,String versionDate);

    /**
     * 文件集
     *
     * @param kbId
     * @return
     */
    List<KnowledgeBaseList> collectList(Long kbId, Integer fileListType);

    /**
     * 通过知识库id和组id查询(返回多条记录)
     *
     * @param groupIds
     * @param kbId
     * @return
     */
    List<KnowledgeBaseList> findByKbIdAndGroupIds(Long kbId, List<String> groupIds, List<Integer> parseTypes);

    /**
     * 通过知识库查询未解析或为抽取的文件
     *
     * @param kbId
     * @param excludeFolderIds
     * @param excludeFileIds
     * @param parseStatus
     * @param faqExtractStatus
     * @return
     */
    List<KnowledgeBaseList> findByKbId(Long kbId, List<Integer> parseTypes, List<Long> excludeFolderIds, List<Long> excludeFileIds, List<Integer> parseStatus, List<Integer> faqExtractStatus);

    /**
     * 查询散落的文件
     *
     * @param kbId
     * @return
     */
    List<KnowledgeBaseList> scatterList(Long kbId, Integer fileListType);

    /**
     * 查询文件的分组信息
     *
     * @param kbId
     * @param groupId
     * @param parseTypes
     * @return
     */
    KnowledgeBaseList findFileGroup(Long kbId, String groupId, List<Integer> parseTypes);

    /**
     * 更新标签
     *
     * @param fileIds
     * @param label
     */
    void updateLabels(List<Long> fileIds, String label);

    void transferFile(Long id, Long folderId);

    void transferFileBatch(List<Long> ids, Long folderId);

    Page<KbFileExt> folderAndFileList(FolderAndFilerReq params, Integer pageNo, Integer pageSize);

    List<KnowledgeBaseList> findByFolderId(Long kbId, Integer type, Long folerId);

    List<KnowledgeBaseList> findFileByFilePaths(Long kbId, List<String> filePaths, Integer code);

    List<FileChunkDTO> getFileChunks(Long docId, Integer pageNo, Integer pageSize);

    List<FileMetadataChunkDTO> getFileMetadataChunks(Long docId, Integer pageNo, Integer pageSize);

    JSONObject getChunks(Long docId, Integer pageNo, Integer pageSize);

    Long getSequenceCodeByFileId(Long fileId);

    /**
     * 更新解析状态
     * @param fileIds
     * @param status
     * @param needUpdateTime 是否需要更新修改时间
     */
    void updateParseStatusByIds(List<Long> fileIds, Integer status, Boolean needUpdateTime);

    void updateGraphExtractByIds(List<Long> graphExtractFileIds, Integer graphExtractStatus);
}
