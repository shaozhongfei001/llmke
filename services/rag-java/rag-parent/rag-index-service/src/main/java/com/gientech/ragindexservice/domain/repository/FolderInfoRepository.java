package com.gientech.ragindexservice.domain.repository;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.request.QueryFolderReq;
import com.gientech.ragindexservice.domain.entity.FolderInfo;
import org.jodconverter.local.office.utils.Lo;

import java.util.List;
import java.util.Set;

public interface FolderInfoRepository {

    FolderInfo findById(Long id);

    List<FolderInfo> findParentIdsById(Long id);

    Set<FolderInfo> findSubFolderById(Long id);

    Set<Long> findParentIdsByIds(List<Long> ids);

    Long save(FolderInfo folderInfo);

    Boolean updateById(FolderInfo folderInfo);

    Page<FolderInfo> list(Long pageNo, Long pageSize);

    Boolean deleteById(Long id);

    /**
     * 根据知识库id和完整路径获取文件夹数据
     *
     * @param kbId
     * @param fullPath
     * @return
     */
    FolderInfo getByKbIdAndFullPath(Long kbId, String fullPath);

    FolderInfo findByKbIdAndName(Long kbId, String name);

    FolderInfo find(Long kbId, String name, Long parentId,Integer type);

    /**
     * 获取当前文件夹的下层子文件夹
     *
     * @param kbId
     * @param folderId
     * @return
     */
    List<FolderInfo> getSubFolderList(Long kbId, Long folderId);

    List<FolderInfo> leveList(List<Long> kbIds);

    List<FolderInfo> findByParentIds(List<Long> ids);

    Boolean deleteByIds(List<Long> ids);

    Boolean updateFolderInfoKbId(FolderInfo folderInfo, Long kbId);

    void transferFolder(Long id, Long parentId);

    void transferFolderBatch(List<Long> ids, Long parentId);

    List<FolderInfo> recursiveFolderByKb(QueryFolderReq queryFolderReq);

    List<FolderInfo> findByFullPaths(Long kbId, List<String> fullPaths, Integer folderType);

    List<FolderInfo> folderList(Long kbId, Integer type, Long folderPid);

    List<FolderInfo> folderList(Long kbId, Integer type);

    List<FolderInfo> findByIds(List<Long> ids);
}
