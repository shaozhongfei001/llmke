package com.gientech.ragindexservice.application.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.JsonNode;
import com.gientech.ragcommon.index.dto.*;
import com.gientech.ragcommon.index.request.*;
import com.gientech.ragcommon.index.utils.JSONPagination;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragindexservice.domain.entity.KbFileExt;
import com.gientech.start.storage.exception.FileStorageException;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.HttpHeaders;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.InputStream;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

/**
 * <p>
 * 知识库明细 服务类
 * </p>
 *
 * @author wudf
 * @since 2024-06-04
 */
public interface KnowledgeBaseListAppService {

    /**
     * 分页查询数据
     *
     * @param req
     * @return
     */
    Page<KnowledgeBaseFileDTO> list(KnowledgeBaseFileQueryReq req);

    /**
     * 通过id删除
     *
     * @param id
     * @return
     */
    Boolean deleteById(Long id);

    /**
     * 上传文件
     *
     * @param kbId
     * @param isOverwrite
     * @return
     * @paramfile
     */
    KnowledgeBaseFileDTO uploadFile(Long kbId, Long fileId, String userId, MultipartFile file, List<MultipartFile> imagesFiles, List<MultipartFile> tableFiles, boolean isOverwrite);

    /**
     * 文件解析(采用mq形式进行解析)
     *
     * @param filesParseReq
     * @return
     */
    Boolean filesParseNew(FilesParseReq filesParseReq);

    /**
     * 文件FAQ抽取
     *
     * @param filesParseReq
     * @return
     */
    Boolean filesExtractFAQNew(FilesParseReq filesParseReq);

    /**
     * 判断文件是否上传过，是否存在分片，断点续传
     *
     * @param fileMd5
     * @return -1 文件没有上传过; -2 文件已存在; 文件上传中断过，返回当前已经上传到的下标
     */
    Integer checkCunkFile(Long kbId, String fileName, String fileMd5);

    /**
     * 上传文件片段
     *
     * @param fileMd5
     * @param file
     * @return
     */
    Boolean chunkUpload(String fileMd5, MultipartFile file);

    /**
     * 文件片段合并
     *
     * @param fileMergeReq
     * @return
     */
    Boolean chunkMerge(FileMergeReq fileMergeReq);

    /**
     * 修改文件状态
     *
     * @param fileEnableReq
     * @return
     */
    Boolean updateEnable(FileEnableReq fileEnableReq);

    /**
     * 查询状态
     *
     * @param fileId
     * @return
     */
    Integer getFileStatusById(Long fileId);

    /**
     * 获取文件详情
     *
     * @param id
     * @return
     */
    KnowledgeBaseFileDTO getById(Long id);


    List<KnowledgeBaseFileDTO> getByIds(Long[] ids);

    /**
     * 获取文件chunk
     *
     * @param docId    文件Id
     * @param pageNo   页码
     * @param pageSize 页面大小
     * @return
     */
    List<FileChunkDTO> getFileChunks(Long docId, Integer pageNo, Integer pageSize);

    List<FileMetadataChunkDTO> getFileMetadataChunks(Long docId, Integer pageNo, Integer pageSize);

    void updateParseStatusByIds(List<Long> fileIds, Integer status, Boolean needUpdateTime);

    /**
     * 获取文件chunk数量
     *
     * @param docId 文件Id
     * @return
     */
    Integer getFileChunkCount(Long docId);
    /**
     * 获取文件解析后的chunk
     *
     * @param kbId  知识库Id
     * @param docId 文件Id
     * @return
     */
    List<FileChunkDTO> getFileChunks(Long kbId, Long docId) throws ApplicationException;

    /**
     * 分页获取文件解析后的chunk
     *
     * @param kbId     知识库Id
     * @param docId    文件Id
     * @param pageNo   页码
     * @param pageSize 页面大小
     * @return
     */
    Page<FileChunkDTO> getFileChunksByPage(Long kbId, Long docId, Integer pageNo, Integer pageSize) throws ApplicationException;

    /**
     * 获取faq抽取状态
     *
     * @param fileId
     * @return
     */
    Integer getFAQExtractStatusById(Long fileId);

    /**
     * 通过id批量删除文件
     *
     * @param fileIds
     * @return
     */
    Boolean deleteByIds(List<Long> fileIds);

    /**
     * 批量上传文件(校验文件重复性)
     *
     * @param uploadFileParam
     * @return
     */
    Object uploadFileList(String uploadFileParam, MultipartFile[] files, boolean chunking);

    Object uploadFileList(String uploadFileParam, MultipartFile[] files);


    /**
     * 校验文件名是否重复
     *
     * @param fileNameList
     * @return
     */
    Set<String> precheck(List<String> fileNameList);

    /**
     * 查询父文件
     *
     * @param req
     * @return
     */
    Page<KnowledgeBaseFileDTO> listNew(KnowledgeBaseFileQueryReq req);

    /**
     * 修订时间
     *
     * @param fileId
     * @param reviseDate
     * @return
     */
    Boolean filesReviseDate(Long fileId, String reviseDate);

    /**
     * 文本chunk关联图片chunk调整
     *
     * @param chunkChangeReq
     * @return
     */
    Boolean chunkChange(ChunkChangeReq chunkChangeReq);

//    /**
//     * 获取文件的修订日期
//     * @param filesParseReq
//     * @return
//     */
//    Boolean filesReviseDate(FilesParseReq filesParseReq);

    /**
     * 从url列表导入文件(包含文件重复性校验、父文件、多版本)
     *
     * @param importUrlListParam
     * @return
     */
    Object importUrlList(String importUrlListParam);

    /**
     * 知识库文件列表(包含文件夹)
     *
     * @param req
     * @return
     */
    Page<KnowledgeBaseFileDTO> folderList(KnowledgeBaseFileQueryReq req);

    LinkedHashSet<KnowledgeBaseFileDTO> fileList(KnowledgeBaseFileQueryReq req);

    LinkedHashSet<KnowledgeBaseFileDTO> flatList(KnowledgeBaseFileQueryReq req);

    Page<KnowledgeBaseFileDTO> flatFiles(KnowledgeBaseFileQueryReq req);

    List<KnowledgeBaseFileDTO> onlyFileListByTime(KnowledgeBaseFileQueryReq req);

    /**
     * 通过id更新文本块内容
     *
     * @param updateChunkReq
     * @return
     */
    Boolean updateChunk(UpdateChunkReq updateChunkReq);

    /**
     * 删除文本块
     *
     * @param deleteChunkReq
     * @return
     */
    Boolean deleteChunk(DeleteChunkReq deleteChunkReq);

    /**
     * faq重新抽取
     *
     * @param filesParseReq
     * @return
     */
    Boolean reExtractFQA(FilesParseReq filesParseReq);

    /**
     * 一键解析
     *
     * @param kbId
     * @return
     */
    Boolean filesAllParse(Long kbId);

    /**
     * 一键抽取
     *
     * @param kbId
     * @return
     */
    Boolean extractAllFQA(Long kbId);

    /**
     * 图解析
     *
     * @param filesParseReq
     * @return
     */
    Boolean graphParse(FilesParseReq filesParseReq);

    /**
     * 查询图解析状态
     *
     * @param fileId
     * @return
     */
    Integer getGraphParseStatus(Long fileId);

    /**
     * 文集预览
     *
     * @param response
     * @param fileUrl
     */
    void viewFile(HttpServletResponse response, String fileUrl) throws IOException;

    /**
     * 通过知识库查询文件
     *
     * @param kbId
     * @return
     */
    List<KnowledgeBaseFileDTO> queryList(Long kbId, List<Integer> types);

    /**
     * 文档上传(仅供文档问答使用)
     *
     * @param files
     * @return
     */
    Object docUploadFile(String sessionId, List<String> uids, MultipartFile[] files);

    /**
     * 通过知识库名和文件fileuIds查询文件，fileUids如果是null，查询当前知识库下所有的文件
     *
     * @param kbName
     * @param fileUids
     * @return
     */
    List<KnowledgeBaseFileDTO> getByKbNameAndUid(String kbName, List<String> fileUids);

    /**
     * 通过uid查询文件解析状态
     *
     * @param uids
     * @return
     */
    List<FileStatusDTO> getFileStatusByUids(List<String> uids);

    List<KnowledgeBaseFileDTO> queryListWithPermission(Long kbId);

    /**
     * 查询文档创建者
     *
     * @param id
     * @return
     */
    String queryCreator(Long id);

    /**
     * 判断文件是否上传过
     *
     * @param kbName
     * @param fileName
     * @param type
     * @return
     */
    Boolean exist(String kbName, String fileName, Integer type);

    /**
     * 创建文件集
     *
     * @param createCollectReq
     * @return
     */
    Boolean createCollect(CreateCollectReq createCollectReq);

    /**
     * 将文件移除文件集
     *
     * @param removeCollectReq
     * @return
     */
    Boolean remove(RemoveCollectReq removeCollectReq);

    /**
     * 文件转移到别的文件集中
     *
     * @param fileCollectTransferReq
     * @return
     */
    Boolean transfer(FileCollectTransferReq fileCollectTransferReq);

    /**
     * 将文件从文件集解散
     *
     * @param dissolveCollectReq
     * @return
     */
    Boolean dissolve(DissolveCollectReq dissolveCollectReq);

    /**
     * 查询知识库下的文件集数据
     *
     * @param kbId
     * @return
     */
    List<CollectDTO> collectList(Long kbId, Integer fileListType);

    /**
     * 通过文件集id查询
     *
     * @param kbId
     * @param groupId
     * @return
     */
    List<KnowledgeBaseFileDTO> getByGroupId(Long kbId, String groupId, Integer fileListType);

    /**
     * 文件归集-散落的文件
     *
     * @param kbId
     * @param fileListType 1文件解析  2 FAQ
     * @return
     */
    List<KnowledgeBaseFileDTO> scatterList(Long kbId, Integer fileListType);

    /**
     * 通过知识库名和文件名查询文本块
     *
     * @param kbName
     * @param fileName
     * @param pageNo
     * @param pageSize
     * @return
     */
    List<FileChunkDTO> getKbFileChunks(String kbName, String fileName, Integer pageNo, Integer pageSize);

    /**
     * 给文件添加标签
     *
     * @param fileId
     * @param label
     * @return
     */
    Boolean addLabel(Long fileId, String label);

    /**
     * 文件多版本结构
     *
     * @param req
     * @return
     */
    Page<KnowledgeBaseFileDTO> multipleVersion(KnowledgeBaseFileQueryReq req);

    InputStream pageFileStream(PageFileStreamReq pageFileStreamReq, HttpHeaders headers) throws IOException, FileStorageException;

    JSONPagination.PageResult<JsonNode> pageFile(PageFileStreamReq pageFileStreamReq, HttpHeaders headers) throws IOException, FileStorageException;

    Integer totalPages(Long fileId);

    Long getSequenceCodeByFileId(Long fileId);

    /**
     * 通过uid删除文件
     *
     * @param fileUid
     * @return
     */
    List<KnowledgeBaseFileDTO> deleteByUid(String queryId, String fileUid);
}
