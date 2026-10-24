package com.gientech.ragindexservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.index.enmus.FolderSatusEnums;
import com.gientech.ragcommon.index.request.QueryFolderReq;
import com.gientech.ragindexservice.domain.entity.FolderInfo;
import com.gientech.ragindexservice.domain.mapper.FolderInfoMapper;
import com.gientech.ragindexservice.domain.model.FolderInfoDO;
import com.gientech.ragindexservice.domain.repository.FolderInfoRepository;
import com.google.common.collect.Lists;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import org.springframework.util.CollectionUtils;

import java.util.*;
import java.util.stream.Collectors;

@Repository
public class FolderInfoRepositoryImpl implements FolderInfoRepository {

    @Autowired
    private FolderInfoMapper folderInfoMapper;

    @Override
    public FolderInfo findById(Long id) {
        if (Objects.isNull(id))
            return null;
        QueryWrapper<FolderInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.lambda().eq(FolderInfoDO::getId, id)
                .eq(FolderInfoDO::getStatus, FolderSatusEnums.NORMAL.getCode());
        FolderInfoDO folderInfoDO = folderInfoMapper.selectOne(queryWrapper);
        return Objects.isNull(folderInfoDO) ? null : BeanUtil.copyProperties(folderInfoDO, FolderInfo.class);
    }

    @Override
    public List<FolderInfo> findByIds(List<Long> ids) {
        if (CollectionUtils.isEmpty(ids))
            return null;
        QueryWrapper<FolderInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.lambda().in(FolderInfoDO::getId, ids)
                .eq(FolderInfoDO::getStatus, FolderSatusEnums.NORMAL.getCode());
        List<FolderInfoDO> folderInfoDOS = folderInfoMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(folderInfoDOS) ? null : BeanUtil.copyToList(folderInfoDOS, FolderInfo.class);
    }

    /**
     * 为了把当前文件夹的父文件夹剔除
     *
     * @param id
     * @return
     */
    @Override
    public List<FolderInfo> findParentIdsById(Long id) {
        List<FolderInfoDO> folderInfoDOS = folderInfoMapper.findParentIdsById(id);
        return CollectionUtils.isEmpty(folderInfoDOS) ? List.of() : BeanUtil.copyToList(folderInfoDOS, FolderInfo.class);
    }

    @Override
    public Set<FolderInfo> findSubFolderById(Long id) {
        List<FolderInfoDO> folderInfoDOS = folderInfoMapper.findSubFolderById(id);
        return CollectionUtils.isEmpty(folderInfoDOS) ? Set.of() : new HashSet<>(BeanUtil.copyToList(folderInfoDOS, FolderInfo.class));
    }

    @Override
    public Set<Long> findParentIdsByIds(List<Long> ids) {
        if (CollectionUtils.isEmpty(ids)) {
            return null;
        }
        List<FolderInfoDO> folderInfoDOS = folderInfoMapper.findParentIdsByIds(ids);
        List<FolderInfo> folderInfoList = CollectionUtils.isEmpty(folderInfoDOS) ? List.of() : BeanUtil.copyToList(folderInfoDOS, FolderInfo.class);
        return folderInfoList.stream().map(FolderInfo::getId).collect(Collectors.toSet());
    }

    @Override
    public Long save(FolderInfo folderInfo) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        folderInfo.setUpdateBy(userName);
        folderInfo.setCreateBy(userName);
        folderInfo.setGmtCreate(new Date());
        folderInfo.setGmtModified(folderInfo.getGmtCreate());
        if (StringUtils.isEmpty(folderInfo.getFullPath())) {
            if (folderInfo.getParentId() == null) {
                folderInfo.setFullPath(folderInfo.getName() + "/");
            } else {
                FolderInfo parentFolderInfo = findById(folderInfo.getParentId());
                folderInfo.setFullPath(parentFolderInfo.getFullPath() + folderInfo.getName() + "/");
            }
        }
        FolderInfoDO folderInfoDO = BeanUtil.copyProperties(folderInfo, FolderInfoDO.class);
        int result = folderInfoMapper.insert(folderInfoDO);
        folderInfo.setId(folderInfoDO.getId());
        return folderInfoDO.getId();
    }

    @Override
    public Boolean updateById(FolderInfo folderInfo) {
        if (Objects.isNull(folderInfo.getId()))
            return false;
        User user = UserContext.getUser();
        String userName = user.getUserName();
        folderInfo.setUpdateBy(userName);
        folderInfo.setGmtModified(new Date());
        if (folderInfo.getParentId() == null) {
            folderInfo.setFullPath(folderInfo.getName() + "/");
        } else {
            FolderInfo parentFolderInfo = findById(folderInfo.getParentId());
            folderInfo.setFullPath(parentFolderInfo.getFullPath() + folderInfo.getName() + "/");
        }
        return folderInfoMapper.updateById(BeanUtil.copyProperties(folderInfo, FolderInfoDO.class)) > 0;
    }

    @Override
    public Page<FolderInfo> list(Long pageNo, Long pageSize) {
        QueryWrapper<FolderInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.orderByDesc("gmt_create");
        queryWrapper.eq("status", FolderSatusEnums.NORMAL.getCode());
        Page<FolderInfoDO> page = new Page<>(pageNo, pageSize);
        Page<FolderInfoDO> pageResult = folderInfoMapper.selectPage(page, queryWrapper);
        Page<FolderInfo> listPage = new Page<>();
        BeanUtil.copyProperties(pageResult, listPage);
        listPage.setRecords(BeanUtil.copyToList(pageResult.getRecords(), FolderInfo.class));
        return listPage;
    }

    @Override
    public Boolean deleteById(Long id) {
        FolderInfo folderInfo = new FolderInfo();
        folderInfo.setId(id);
        folderInfo.setStatus(FolderSatusEnums.DELETE.getCode());
        return folderInfoMapper.updateById(BeanUtil.copyProperties(folderInfo, FolderInfoDO.class)) > 0;
    }

    @Override
    public Boolean deleteByIds(List<Long> ids) {
        if(CollectionUtils.isEmpty(ids))
            return false;
        QueryWrapper<FolderInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.in("id", ids).eq("status", FolderSatusEnums.NORMAL.getCode());

        FolderInfoDO folderInfoDO = new FolderInfoDO();
        folderInfoDO.setStatus(FolderSatusEnums.DELETE.getCode());
        return folderInfoMapper.update(folderInfoDO, queryWrapper) > 0;
    }

    @Override
    public FolderInfo getByKbIdAndFullPath(Long kbId, String fullPath) {
        QueryWrapper<FolderInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper
                .eq("kb_id", kbId)
                .eq("status", FolderSatusEnums.NORMAL.getCode())
                .eq("full_path", fullPath);
        List<FolderInfoDO> folderInfoDOS = folderInfoMapper.selectList(queryWrapper);
        if (!CollectionUtils.isEmpty(folderInfoDOS)) {
            return BeanUtil.copyProperties(folderInfoDOS.get(0), FolderInfo.class);
        }
        return null;
    }

    @Override
    public FolderInfo findByKbIdAndName(Long kbId, String name) {
        QueryWrapper<FolderInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("kb_id", kbId);
        queryWrapper.eq("status", FolderSatusEnums.NORMAL.getCode());
        queryWrapper.eq("name", name);
        queryWrapper.last("limit 1");
        FolderInfoDO folderInfoDO = folderInfoMapper.selectOne(queryWrapper);
        return Objects.isNull(folderInfoDO) ? null : BeanUtil.copyProperties(folderInfoDO, FolderInfo.class);
    }

    @Override
    public FolderInfo find(Long kbId, String name, Long parentId, Integer type) {
        QueryWrapper<FolderInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("kb_id", kbId);
        queryWrapper.eq(Objects.nonNull(type), "type", type);
        queryWrapper.eq("status", FolderSatusEnums.NORMAL.getCode());
        queryWrapper.eq("name", name);
        if (Objects.isNull(parentId)) {
            queryWrapper.isNull("parent_id");
        } else {
            queryWrapper.eq("parent_id", parentId);
        }
        queryWrapper.last("limit 1");
        FolderInfoDO folderInfoDO = folderInfoMapper.selectOne(queryWrapper);
        return Objects.isNull(folderInfoDO) ? null : BeanUtil.copyProperties(folderInfoDO, FolderInfo.class);
    }

    @Override
    public List<FolderInfo> getSubFolderList(Long kbId, Long folderId) {
        QueryWrapper<FolderInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper
                .eq("kb_id", kbId)
                .eq("status", FolderSatusEnums.NORMAL.getCode())
                .eq("parent_id", folderId);
        List<FolderInfoDO> folderInfoDOS = folderInfoMapper.selectList(queryWrapper);
        if (!CollectionUtils.isEmpty(folderInfoDOS)) {
            return BeanUtil.copyToList(folderInfoDOS, FolderInfo.class);
        }
        return null;
    }

    @Override
    public List<FolderInfo> leveList(List<Long> kbIds) {
        QueryWrapper<FolderInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.in("kb_id", kbIds);
        queryWrapper.eq("status", FolderSatusEnums.NORMAL.getCode());
        List<FolderInfoDO> folderInfoDOList = folderInfoMapper.selectList(queryWrapper);
        return Objects.isNull(folderInfoDOList) ? null : BeanUtil.copyToList(folderInfoDOList, FolderInfo.class);
    }

    @Override
    public List<FolderInfo> findByParentIds(List<Long> ids) {
        QueryWrapper<FolderInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.in("parent_id", ids);
        queryWrapper.eq("status", FolderSatusEnums.NORMAL.getCode());
        List<FolderInfoDO> folderInfoDOList = folderInfoMapper.selectList(queryWrapper);
        return Objects.isNull(folderInfoDOList) ? null : BeanUtil.copyToList(folderInfoDOList, FolderInfo.class);
    }

    @Override
    public Boolean updateFolderInfoKbId(FolderInfo folderInfo, Long kbId) {
        folderInfo.setKbId(kbId);
        return folderInfoMapper.updateById(BeanUtil.copyProperties(folderInfo, FolderInfoDO.class)) > 0;
    }

    @Override
    public void transferFolder(Long id, Long parentId) {
        folderInfoMapper.transferFolder(id, parentId);
    }

    @Override
    public void transferFolderBatch(List<Long> ids, Long parentId) {
        if (!CollectionUtils.isEmpty(ids))
            folderInfoMapper.transferFolderBatch(ids, parentId);
    }

    @Override
    public List<FolderInfo> recursiveFolderByKb(QueryFolderReq queryFolderReq) {
        Long kbId = queryFolderReq.getKbId();
        Integer type = queryFolderReq.getType();
        Set<Long> currentIds = new HashSet<>();
        Set<Long> currentFileIds = new HashSet<>();

        buildRequestParam(queryFolderReq, currentIds, currentFileIds);

        return BeanUtil.copyToList(folderInfoMapper.recursiveFolderByKb(kbId, type, currentIds, currentFileIds), FolderInfo.class);
    }

    private void buildRequestParam(QueryFolderReq queryFolderReq, Set<Long> currentIds, Set<Long> currentFileIds) {
        Long currentId = queryFolderReq.getCurrentId();
        List<Long> currentFileIdsParam = queryFolderReq.getCurrentFileIds();
        List<Long> currentIdsParam = queryFolderReq.getCurrentIds();


        if (!CollectionUtils.isEmpty(currentIdsParam)) {
            currentIds.addAll(currentIdsParam);
            currentFileIds.addAll(findParentIdsByIds(new ArrayList<>(currentIds)));
        }
        if (!CollectionUtils.isEmpty(currentFileIdsParam)) {
            currentFileIds.addAll(currentFileIdsParam);
            currentFileIds.addAll(findParentIdsByIds(new ArrayList<>(currentFileIds)));
        }
        if (Objects.nonNull(currentId)) {
            currentIds.add(currentId);
            FolderInfo folderInfo = findById(currentId);
            Long currentFolderParentId = Objects.isNull(folderInfo) ? null : folderInfo.getParentId();
            currentFileIds.add(currentFolderParentId);
        }
    }

    @Override
    public List<FolderInfo> findByFullPaths(Long kbId, List<String> fullPaths, Integer folderType) {
        QueryWrapper<FolderInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.lambda().eq(FolderInfoDO::getKbId, kbId)
                .in(FolderInfoDO::getFullPath, fullPaths)
                .eq(FolderInfoDO::getType, folderType)
                .eq(FolderInfoDO::getStatus, FolderSatusEnums.NORMAL.getCode());
        List<FolderInfoDO> folderInfoDOS = folderInfoMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(folderInfoDOS) ? Lists.newArrayList() : BeanUtil.copyToList(folderInfoDOS, FolderInfo.class);
    }

    @Override
    public List<FolderInfo> folderList(Long kbId, Integer type, Long folderPid) {
        QueryWrapper<FolderInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.lambda().eq(FolderInfoDO::getKbId, kbId)
                .eq(FolderInfoDO::getType, type)
                .eq(FolderInfoDO::getStatus, FolderSatusEnums.NORMAL.getCode());
        if(Objects.isNull(folderPid))
            queryWrapper.lambda().isNull(FolderInfoDO::getParentId);
        else
            queryWrapper.lambda().eq(FolderInfoDO::getParentId,folderPid);
        List<FolderInfoDO> folderInfoDOS = folderInfoMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(folderInfoDOS) ? Lists.newArrayList() : BeanUtil.copyToList(folderInfoDOS, FolderInfo.class);
    }

    @Override
    public List<FolderInfo> folderList(Long kbId, Integer type) {
        QueryWrapper<FolderInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.lambda().eq(FolderInfoDO::getKbId, kbId)
                .eq(FolderInfoDO::getType, type)
                .eq(FolderInfoDO::getStatus, FolderSatusEnums.NORMAL.getCode());
        queryWrapper.lambda().isNotNull(FolderInfoDO::getParentId);
        List<FolderInfoDO> folderInfoDOS = folderInfoMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(folderInfoDOS) ? Lists.newArrayList() : BeanUtil.copyToList(folderInfoDOS, FolderInfo.class);
    }
}
