package com.gientech.ragindexservice.domain.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.request.QueryFolderReq;
import com.gientech.ragindexservice.domain.entity.FolderInfo;

import java.util.List;
import java.util.Set;

public interface FolderInfoDomainService {

    FolderInfo findById(Long id);

    List<FolderInfo> findByIds(List<Long> ids);

    List<FolderInfo> findParentIdsById(Long id);

    Set<FolderInfo> findSubFolderById(Long id);

    List<FolderInfo> findByParentIds(List<Long> ids);

    Boolean save(FolderInfo folderInfo);

    Boolean updateById(FolderInfo folderInfo);

    Page<FolderInfo> list(Long pageNo, Long pageSize);

    Boolean deleteById(Long id);

    Boolean deleteByIds(List<Long> ids);

    /**
     * 根据知识库id和完整路径获取文件夹数据
     *
     * @param kbId
     * @param fullPath
     * @return
     */
    FolderInfo getByKbIdAndFullPath(Long kbId, String fullPath);

    FolderInfo findByKbIdAndName(Long kbId, String name);

    FolderInfo find(Long kbId, String name, Long parentId, Integer type);

    List<FolderInfo> leveList(List<Long> kbIds);

    Boolean updateFolderInfoKbId(FolderInfo folderInfo, Long kbId);

    String queryCreator(Long id);

    void transferFolder(Long id, Long parentId);

    void transferFolderBatch(List<Long> ids, Long parentId);

    List<FolderInfo> recursiveFolderByKb(QueryFolderReq queryFolderReq);

    /**
     * 通过fullPath创建文件夹   文件夹2/文件夹2_1/
     * @param kbId
     * @param fullPath
     * @return
     */
    Long createFolderByFullPath(Long kbId, String fullPath,Integer type);

    List<FolderInfo> findByFullPaths(Long kbId, List<String> fullPaths,Integer folderType);

    List<FolderInfo> folderList(Long kbId, Integer type, Long folderPid);

    List<FolderInfo> folderList(Long kbId, Integer type);

    /**
     * 根据当前文件夹，递归获取子文件件夹id
     * @param folderIds
     * @param childrenFolderIds
     */
    void getChildrenFolderIds(List<Long> folderIds, List<Long> childrenFolderIds);

    void getChildrenFolders(List<FolderInfo> folders, List<FolderInfo> childrenFolders);

    /**
     * 根据当前文件夹查询文件夹
     * @param folderIds
     * @param parentFolderIds
     */
    void getParentFolderIds(List<Long> folderIds, List<Long> parentFolderIds);
}
