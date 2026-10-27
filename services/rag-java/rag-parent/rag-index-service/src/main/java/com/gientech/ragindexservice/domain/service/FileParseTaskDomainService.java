package com.gientech.ragindexservice.domain.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragindexservice.domain.entity.FileParseTask;

import java.util.List;

public interface FileParseTaskDomainService {

    FileParseTask findById(Long id);

    Boolean save(FileParseTask fileParseTask);

    Boolean saveBatch(List<FileParseTask> fileParseTasks);

    Boolean updateById(FileParseTask fileParseTask);

    Page<FileParseTask> list(Long pageNo, Long pageSize);

    Boolean deleteById(Long id);

    List<FileParseTask> getExeIngTaskList();

    List<FileParseTask> getTaskList(List<Integer> taskStatus, Integer limit);

    void updateStatusByIds(List<Long> taskIds, Integer status);

    /** R14-C-FIX-32：派发前原子抢占（CAS），返回 true 表示本次调用抢到了该任务。 */
    boolean claimTask(Long id, Integer toStatus, List<Integer> fromStatus);

    void deleteByFileIds(List<Long> fileIds);

    void deleteByKbIds(List<Long> kbIds);

    FileParseTask getByFileId(Long fileId);

    Long getSequenceByFileId(Long fileId);

    List<FileParseTask> getTaskByStatus(List<Integer> taskStatus);
}
