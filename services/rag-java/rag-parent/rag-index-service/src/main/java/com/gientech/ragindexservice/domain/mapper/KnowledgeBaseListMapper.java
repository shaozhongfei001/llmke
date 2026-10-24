package com.gientech.ragindexservice.domain.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.request.FolderAndFilerReq;
import com.gientech.ragindexservice.domain.entity.KbFileExt;
import com.gientech.ragindexservice.domain.entity.KnowledgeBaseList;
import com.gientech.ragindexservice.domain.model.KnowledgeBaseFileDO;
import com.gientech.ragindexservice.domain.model.KnowledgeBaseListDO;
import org.apache.ibatis.annotations.MapKey;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Update;

import java.time.LocalDateTime;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;


/**
 * <p>
 * 知识库明细 Mapper 接口
 * </p>
 *
 * @author wudf
 * @since 2024-08-02
 */
@Mapper
public interface KnowledgeBaseListMapper extends BaseMapper<KnowledgeBaseListDO> {

    void saveBatch(@Param("list") List<KnowledgeBaseListDO> knowledgeBaseListDOS);

    void updateStatusByFilePaths(@Param("filePaths") List<String> filePaths, @Param("status") Integer status);

    void updateStatusByIds(@Param("ids") List<Long> ids, @Param("status") Integer status, @Param("pathSetNull") boolean pathSetNull);

    @MapKey("kbId")
    Map<Long, KnowledgeBaseFileDO> selectFiles(@Param("kbIds") List<Long> kbIds);

    void updateExtractStatusByFilePaths(@Param("filePaths") List<String> filePaths, @Param("extractStatus") Integer extractStatus);

    List<KnowledgeBaseListDO> findFileMaxVersion(@Param("kbId") Long kbId, @Param("fileListType") Integer fileListType);

    Long parentListCount(
            @Param("kbId") Long kbId, @Param("fileListType") Integer fileListType,
            @Param("fuzzy") String fuzzy, @Param("status") Integer status,
            @Param("faqExtractStatus") Integer faqExtractStatus,
            @Param("showType") Integer showType,
            @Param("kbIds") List<Long> kbIds
    );

    List<KnowledgeBaseListDO> parentList(
            @Param("kbId") Long kbId, @Param("fileListType") Integer fileListType,
            @Param("fuzzy") String fuzzy, @Param("status") Integer status,
            @Param("faqExtractStatus") Integer faqExtractStatus,
            @Param("showType") Integer showType,
            @Param("kbIds") List<Long> kbIds,
            @Param("offSet") Long offSet, @Param("pageSize") Long pageSize);

    Integer folderListCount(
            @Param("params") Map<String, Object> params);

    List<KbFileExt> folderList(
            @Param("params") Map<String, Object> params);

    Page<KbFileExt> folderAndFileList(Page<KbFileExt> page, @Param("params") FolderAndFilerReq params);

    LinkedHashSet<KbFileExt> fileList(
            @Param("kbIds") List<Long> kbIds, @Param("status") Integer status,
            @Param("kbName") String kbName, @Param("folderIds") Set<Long> folderIds, @Param("userName") String userName, @Param("withFolder") boolean withFolder);

    Page<KbFileExt> onlyFileList(IPage<KbFileExt> page,
                                 @Param("kbIds") List<Long> kbIds, @Param("statusArray") int[] status,
                                 @Param("kbName") String kbName, @Param("folderIds") Set<Long> folderIds, @Param("userName") String userName);

    List<KbFileExt> onlyFileListByTime(
            @Param("kbIds") List<Long> kbIds, @Param("statusArray") int[] status,
            @Param("kbName") String kbName, @Param("folderIds") Set<Long> folderIds, @Param("userName") String userName, @Param("startTime") LocalDateTime startTime, @Param("endTime") LocalDateTime endTime);

    void updateExtractStatusByIds(@Param("ids") List<Long> ids, @Param("extractStatus") Integer extractStatus);

    List<KnowledgeBaseListDO> queryListWithPermission(@Param("kbId") Long kbId, @Param("deptId") Long deptId, @Param("userId") Long userId, @Param("folderType") Integer folderType, @Param("parseType") Integer parseType, @Param("bizTypes") List<Integer> bizTypes);

    List<KnowledgeBaseListDO> queryNoPermissionFiles(@Param("kbId") Long kbId, @Param("deptId") Long deptId, @Param("userId") Long userId);

    void updateTempStatusByUid(@Param("uids") List<String> fileUids, @Param("temStatus") Integer temStatus);

    KnowledgeBaseListDO findFileGroup(@Param("kbId") Long kbId, @Param("groupId") String groupId, @Param("parseTypes") List<Integer> parseTypes);

    List<KnowledgeBaseList> recursiveByFolderId(@Param("folderId") Long folderId);

    void transferFile(@Param("fileId") Long fileId, @Param("folderId") Long folderId);

    void transferFileBatch(@Param("fileIds") List<Long> fileIds, @Param("folderId") Long folderId);

    @Update("DROP TABLE IF EXISTS tmp_ids")
    void dropTmpIdsTable();

    @Update("create TABLE tmp_ids (id BIGINT)")
    void createTmpIdsTable();

    void insertTmpIds(@Param("kbIds") Set<Long> kbIds);

    void updateParseStatusByIds(@Param("ids") List<Long> fileIds, @Param("status") Integer status, @Param("needUpdateTime") Boolean needUpdateTime);

    Long getSequenceCodeByFileId(@Param("fileId") Long fileId);

    void updateGraphExtractByIds(@Param("ids") List<Long> ids, @Param("graphExtractStatus") Integer graphExtractStatus);
}
