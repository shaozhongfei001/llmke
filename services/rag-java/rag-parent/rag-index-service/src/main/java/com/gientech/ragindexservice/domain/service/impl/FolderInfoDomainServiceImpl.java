package com.gientech.ragindexservice.domain.service.impl;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.enmus.FolderSatusEnums;
import com.gientech.ragcommon.index.enmus.FolderTypeEnums;
import com.gientech.ragcommon.index.request.QueryFolderReq;
import com.gientech.ragindexservice.domain.entity.FolderInfo;
import com.gientech.ragindexservice.domain.repository.FolderInfoRepository;
import com.gientech.ragindexservice.domain.service.FolderInfoDomainService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.util.List;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;

@Service
public class FolderInfoDomainServiceImpl implements FolderInfoDomainService {

    @Autowired
    private FolderInfoRepository folderInfoRepository;

    @Override
    public FolderInfo findById(Long id) {
        return folderInfoRepository.findById(id);
    }

    @Override
    public List<FolderInfo> findByIds(List<Long> ids) {
        return folderInfoRepository.findByIds(ids);
    }

    @Override
    public List<FolderInfo> findParentIdsById(Long id) {
        return folderInfoRepository.findParentIdsById(id);
    }

    @Override
    public Set<FolderInfo> findSubFolderById(Long id) {
        return folderInfoRepository.findSubFolderById(id);
    }

    @Override
    public List<FolderInfo> findByParentIds(List<Long> ids) {
        return folderInfoRepository.findByParentIds(ids);
    }

    @Override
    public Boolean save(FolderInfo folderInfo) {
        return folderInfoRepository.save(folderInfo) > 0;
    }

    @Override
    public Boolean updateById(FolderInfo folderInfo) {
        Boolean result = folderInfoRepository.updateById(folderInfo);
        List<FolderInfo> subFolderInfoList = folderInfoRepository.getSubFolderList(folderInfo.getKbId(), folderInfo.getId());
        if (!CollectionUtils.isEmpty(subFolderInfoList)) {
            for (FolderInfo subFoldInfo : subFolderInfoList) {
                result &= updateById(subFoldInfo);
            }
        }
        return result;
    }

    @Override
    public Page<FolderInfo> list(Long pageNo, Long pageSize) {
        return folderInfoRepository.list(pageNo, pageSize);
    }

    @Override
    public Boolean deleteById(Long id) {
        return folderInfoRepository.deleteById(id);
    }

    @Override
    public Boolean deleteByIds(List<Long> ids) {
        return folderInfoRepository.deleteByIds(ids);
    }

    @Override
    public FolderInfo getByKbIdAndFullPath(Long kbId, String fullPath) {
        return folderInfoRepository.getByKbIdAndFullPath(kbId, fullPath);
    }

    @Override
    public FolderInfo findByKbIdAndName(Long kbId, String name) {
        return folderInfoRepository.findByKbIdAndName(kbId, name);
    }

    @Override
    public FolderInfo find(Long kbId, String name, Long parentId, Integer type) {
        return folderInfoRepository.find(kbId, name, parentId, type);
    }

    @Override
    public List<FolderInfo> leveList(List<Long> kbIds) {
        return folderInfoRepository.leveList(kbIds);
    }

    @Override
    public Boolean updateFolderInfoKbId(FolderInfo folderInfo, Long kbId) {
        return folderInfoRepository.updateFolderInfoKbId(folderInfo, kbId);
    }

    @Override
    public String queryCreator(Long id) {
        FolderInfo folderInfo = folderInfoRepository.findById(id);
        return Objects.isNull(folderInfo) ? null : folderInfo.getCreateBy();
    }

    @Override
    public void transferFolder(Long id, Long parentId) {
        folderInfoRepository.transferFolder(id, parentId);
    }

    @Override
    public void transferFolderBatch(List<Long> ids, Long parentId) {
        folderInfoRepository.transferFolderBatch(ids,parentId);
    }

    @Override
    public List<FolderInfo> recursiveFolderByKb(QueryFolderReq queryFolderReq) {
        List<FolderInfo> folderInfos = folderInfoRepository.recursiveFolderByKb(queryFolderReq);
        return CollectionUtils.isEmpty(folderInfos) ? null : folderInfos;
    }

    @Override
    public Long createFolderByFullPath(Long kbId, String fullPath,Integer type) {
        //fullPath结构 文件夹1/文件夹2/文件夹2_1/
        String folderName;
        Long folderId = null;
        String newFullPath = "";
        while (fullPath.contains("/")){
            folderName = fullPath.substring(0,fullPath.indexOf("/"));
            FolderInfo folderInfo = new FolderInfo();
            folderInfo.setName(folderName);
            folderInfo.setKbId(kbId);
            folderInfo.setType(type);
            folderInfo.setParentId(folderId);
            folderInfo.setStatus(FolderSatusEnums.NORMAL.getCode());
            newFullPath = newFullPath  + folderName + "/";
            folderInfo.setFullPath(newFullPath);
            FolderInfo dbFolder = folderInfoRepository.find(kbId, folderName, folderId, type);
            if(!Objects.isNull(dbFolder))
                folderId = dbFolder.getId();
            else
                folderId = folderInfoRepository.save(folderInfo);
            fullPath = fullPath.substring(fullPath.indexOf("/") + 1);
        }
        return folderId;
    }

    @Override
    public List<FolderInfo> findByFullPaths(Long kbId, List<String> fullPaths,Integer folderType) {
        return folderInfoRepository.findByFullPaths(kbId,fullPaths,folderType);
    }

    @Override
    public List<FolderInfo> folderList(Long kbId, Integer type, Long folderPid) {
        return folderInfoRepository.folderList(kbId,type,folderPid);
    }

    @Override
    public List<FolderInfo> folderList(Long kbId, Integer type) {
        return folderInfoRepository.folderList(kbId,type);
    }

    @Override
    public void getChildrenFolderIds(List<Long> folderIds, List<Long> childrenFolderIds) {
        if (!CollectionUtils.isEmpty(folderIds)) {
            List<FolderInfo> folderInfos = this.findByParentIds(folderIds);
            if (!CollectionUtils.isEmpty(folderInfos)) {
                List<Long> ids = folderInfos.stream().map(FolderInfo::getId).collect(Collectors.toList());
                childrenFolderIds.addAll(ids);
                getChildrenFolderIds(ids, childrenFolderIds);
            }
        }
    }

    @Override
    public void getChildrenFolders(List<FolderInfo> folders, List<FolderInfo> childrenFolders) {
        if (!CollectionUtils.isEmpty(folders)) {
            List<FolderInfo> folderInfos = this.findByParentIds(folders.stream().map(FolderInfo::getId).collect(Collectors.toList()));
            if (!CollectionUtils.isEmpty(folderInfos)) {
                childrenFolders.addAll(folderInfos);
                getChildrenFolders(folderInfos, childrenFolders);
            }
        }
    }

    @Override
    public void getParentFolderIds(List<Long> folderIds, List<Long> parentFolderIds) {
        if (!CollectionUtils.isEmpty(folderIds)) {
            List<FolderInfo> folderInfos = this.findByIds(folderIds);
            if (!CollectionUtils.isEmpty(folderInfos)) {
                List<Long> pids = folderInfos.stream().map(FolderInfo::getParentId).collect(Collectors.toList());
                parentFolderIds.addAll(pids);
                getChildrenFolderIds(pids, parentFolderIds);
            }
        }
    }
}
