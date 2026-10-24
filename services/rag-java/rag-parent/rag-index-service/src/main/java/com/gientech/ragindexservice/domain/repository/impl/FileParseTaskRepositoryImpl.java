package com.gientech.ragindexservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.index.enmus.ParseTaskStatusEnums;
import com.gientech.ragindexservice.domain.entity.FileParseTask;
import com.gientech.ragindexservice.domain.mapper.FileParseTaskMapper;
import com.gientech.ragindexservice.domain.model.FileParseTaskDO;
import com.gientech.ragindexservice.domain.repository.FileParseTaskRepository;
import org.apache.commons.collections4.CollectionUtils;
import org.assertj.core.util.Lists;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;

import java.util.Collections;
import java.util.Date;
import java.util.List;
import java.util.Objects;

@Repository
public class  FileParseTaskRepositoryImpl implements  FileParseTaskRepository {

    @Autowired
    private  FileParseTaskMapper  fileParseTaskMapper;

    @Override
    public FileParseTask findById(Long id) {
        QueryWrapper<FileParseTaskDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.lambda()
                .eq(FileParseTaskDO::getId,id)
                .ne(FileParseTaskDO::getStatus,ParseTaskStatusEnums.DELETED.getCode())
                .last("limit 1");
        FileParseTaskDO fileParseTaskDO = fileParseTaskMapper.selectOne(queryWrapper);
        return Objects.isNull(fileParseTaskDO) ? null : BeanUtil.copyProperties(fileParseTaskDO,FileParseTask.class);
    }

    @Override
    public Boolean save(FileParseTask fileParseTask) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        fileParseTask.setModifyBy(userName);
        fileParseTask.setCreateBy(userName);
        fileParseTask.setGmtCreate(new Date());
        fileParseTask.setGmtModified(fileParseTask.getGmtCreate());
        return fileParseTaskMapper.insert(BeanUtil.copyProperties(fileParseTask, FileParseTaskDO.class)) > 0;
    }

    @Override
    public Boolean updateById(FileParseTask fileParseTask) {
        if (Objects.isNull(fileParseTask.getId()))
            return false;
//        User user = UserContext.getUser();
//        String userName = user.getUserName();
//        fileParseTask.setModifyBy(userName);
        fileParseTask.setGmtModified(new Date());
        return fileParseTaskMapper.updateById(BeanUtil.copyProperties(fileParseTask, FileParseTaskDO.class)) > 0;
    }

    @Override
    public Page<FileParseTask> list(Long pageNo, Long pageSize) {
        QueryWrapper<FileParseTaskDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.orderByDesc("gmt_create");
        Page<FileParseTaskDO> page = new Page<>(pageNo, pageSize);
        Page<FileParseTaskDO> pageResult = fileParseTaskMapper.selectPage(page, queryWrapper);
        Page<FileParseTask> listPage = new Page<>();
        BeanUtil.copyProperties(pageResult,listPage);
        listPage.setRecords(BeanUtil.copyToList(pageResult.getRecords(),FileParseTask.class));
        return listPage;
    }

    @Override
    public Boolean deleteById(Long id) {
        return fileParseTaskMapper.deleteById(id) > 0;
    }

    @Override
    public Boolean saveBatch(List<FileParseTask> fileParseTasks) {
        return fileParseTaskMapper.saveBatch(BeanUtil.copyToList(fileParseTasks,FileParseTaskDO.class));
    }

    @Override
    public List<FileParseTask> getExeIngTaskList() {
        QueryWrapper<FileParseTaskDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.lambda().eq(FileParseTaskDO::getStatus, ParseTaskStatusEnums.DEAL_ING.getCode());
        List<FileParseTaskDO> fileParseTaskDOS = fileParseTaskMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(fileParseTaskDOS) ? Lists.newArrayList() : BeanUtil.copyToList(fileParseTaskDOS,FileParseTask.class);
    }

    @Override
    public List<FileParseTask> getTaskList(List<Integer> taskStatus, Integer limit) {
        List<FileParseTaskDO> fileParseTaskDOS = fileParseTaskMapper.getTaskList(taskStatus,limit);
        return CollectionUtils.isEmpty(fileParseTaskDOS) ? Lists.newArrayList() : BeanUtil.copyToList(fileParseTaskDOS,FileParseTask.class);
    }

    @Override
    public void updateStatusByIds(List<Long> taskIds, Integer status) {
        fileParseTaskMapper.updateStatusByIds(taskIds,status);
    }

    @Override
    public void deleteByFileIds(List<Long> fileIds) {
        if(CollectionUtils.isEmpty(fileIds))
            return;
        fileParseTaskMapper.deleteByFileIds(fileIds);
    }

    @Override
    public void deleteByKbIds(List<Long> kbIds) {
        if(CollectionUtils.isEmpty(kbIds))
            return;
        fileParseTaskMapper.deleteByKbIds(kbIds);
    }

    @Override
    public FileParseTask getByFileId(Long fileId) {
        QueryWrapper<FileParseTaskDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.lambda()
                .eq(FileParseTaskDO::getFileId,fileId)
                .ne(FileParseTaskDO::getStatus, ParseTaskStatusEnums.DELETED.getCode())
                .last("limit 1");
        FileParseTaskDO fileParseTaskDO = fileParseTaskMapper.selectOne(queryWrapper);
        return Objects.isNull(fileParseTaskDO) ? null : BeanUtil.copyProperties(fileParseTaskDO,FileParseTask.class);
    }

    @Override
    public List<FileParseTask> getTaskByStatus(List<Integer> taskStatus) {
        QueryWrapper<FileParseTaskDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.lambda().in(FileParseTaskDO::getStatus,taskStatus);
        List<FileParseTaskDO> fileParseTaskDOS = fileParseTaskMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(fileParseTaskDOS) ? Lists.newArrayList() : BeanUtil.copyToList(fileParseTaskDOS,FileParseTask.class);
    }

    @Override
    public Long getSequenceByFileId(Long fileId) {
       return fileParseTaskMapper.getSequenceByFileId(fileId);
    }
}
