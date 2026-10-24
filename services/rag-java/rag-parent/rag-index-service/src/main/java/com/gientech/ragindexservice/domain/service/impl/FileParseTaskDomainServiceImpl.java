package com.gientech.ragindexservice.domain.service.impl;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragindexservice.domain.entity.FileParseTask;
import com.gientech.ragindexservice.domain.repository.FileParseTaskRepository;
import com.gientech.ragindexservice.domain.service.FileParseTaskDomainService;
import com.google.common.collect.Lists;
import org.apache.commons.collections4.CollectionUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Objects;

@Service
public class FileParseTaskDomainServiceImpl implements FileParseTaskDomainService {

    @Autowired
    private FileParseTaskRepository fileParseTaskRepository;

    @Override
    public FileParseTask findById(Long id) {
        return fileParseTaskRepository.findById(id);
    }

    @Override
    public Boolean save(FileParseTask fileParseTask) {
        return fileParseTaskRepository.save(fileParseTask);
    }

    @Override
    public Boolean updateById(FileParseTask fileParseTask) {
        return fileParseTaskRepository.updateById(fileParseTask);
    }

    @Override
    public Page<FileParseTask> list(Long pageNo, Long pageSize) {
        return fileParseTaskRepository.list(pageNo,pageSize);
    }

    @Override
    public Boolean deleteById(Long id) {
         return fileParseTaskRepository.deleteById(id);
    }

    @Override
    public Boolean saveBatch(List<FileParseTask> fileParseTasks) {
        return !CollectionUtils.isEmpty(fileParseTasks) && fileParseTaskRepository.saveBatch(fileParseTasks);
    }

    @Override
    public List<FileParseTask> getExeIngTaskList() {
        return fileParseTaskRepository.getExeIngTaskList();
    }

    @Override
    public List<FileParseTask> getTaskList(List<Integer> taskStatus, Integer limit) {
        return fileParseTaskRepository.getTaskList(taskStatus,limit);
    }

    @Override
    public void updateStatusByIds(List<Long> taskIds, Integer status) {
        if(CollectionUtils.isEmpty(taskIds))
            return;
        fileParseTaskRepository.updateStatusByIds(taskIds,status);
    }

    @Override
    public void deleteByFileIds(List<Long> fileIds) {
        if(CollectionUtils.isEmpty(fileIds))
            return;
        fileParseTaskRepository.deleteByFileIds(fileIds);
    }

    @Override
    public void deleteByKbIds(List<Long> kbIds) {
        if(CollectionUtils.isEmpty(kbIds))
            return;
        fileParseTaskRepository.deleteByKbIds(kbIds);
    }

    @Override
    public FileParseTask getByFileId(Long fileId) {
        if(Objects.isNull(fileId))
            return null;
        return fileParseTaskRepository.getByFileId(fileId);
    }

    @Override
    public Long getSequenceByFileId(Long fileId) {
        return fileParseTaskRepository.getSequenceByFileId(fileId);
    }

    @Override
    public List<FileParseTask> getTaskByStatus(List<Integer> taskStatus) {
        if(CollectionUtils.isEmpty(taskStatus))
            return Lists.newArrayList();
        return fileParseTaskRepository.getTaskByStatus(taskStatus);
    }
}
