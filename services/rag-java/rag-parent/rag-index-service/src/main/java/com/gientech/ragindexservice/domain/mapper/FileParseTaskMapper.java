package com.gientech.ragindexservice.domain.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.gientech.ragindexservice.domain.model.FileParseTaskDO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface FileParseTaskMapper extends BaseMapper<FileParseTaskDO> {

    Boolean saveBatch(@Param("list") List<FileParseTaskDO> fileParseTasks);

    List<FileParseTaskDO> getTaskList(@Param("taskStatus") List<Integer> taskStatus, @Param("limit") Integer limit);

    void updateStatusByIds(@Param("taskIds") List<Long> taskIds, @Param("status") Integer status);

    /**
     * R14-C-FIX-32：原子抢占。仅当任务当前处于 fromStatus 之一时才改成 toStatus 并写入 start_time；
     * 返回受影响行数（1=抢到，0=已被别人抢走），调用方必须据此决定是否继续派发。
     */
    int claimTask(@Param("id") Long id, @Param("toStatus") Integer toStatus,
                  @Param("fromStatus") List<Integer> fromStatus);

    void deleteByFileIds(@Param("fileIds") List<Long> fileIds);

    void deleteByKbIds(@Param("kbIds") List<Long> kbIds);

    /**
     * R14-LIVE-11：知识库删除时，把它名下仍处于 PENDING(1)/DEAL_ING(2)/RETRY_ING(3) 的任务
     * 一并作废，写清原因。
     *
     * 不这么做的后果（实测）：E2E 测试库 R14-E2E-AG5-1111 被"用完即删"后，它名下的 2 个
     * PENDING 任务永久留在队列里——所属知识库已不存在，永远不会被派发，也不会超时。
     * 表现是队列检查里"最老 PENDING 已等 1321 分钟"的假红，且这些任务长期占用待处理名额。
     */
    int cancelOpenTasksByKb(@Param("kbId") Long kbId, @Param("msg") String msg);

    Long getSequenceByFileId(@Param("fileId") Long fileId);
}