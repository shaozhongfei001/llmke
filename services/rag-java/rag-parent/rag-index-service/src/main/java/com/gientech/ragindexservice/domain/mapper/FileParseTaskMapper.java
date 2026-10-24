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

    void deleteByFileIds(@Param("fileIds") List<Long> fileIds);

    void deleteByKbIds(@Param("kbIds") List<Long> kbIds);

    Long getSequenceByFileId(@Param("fileId") Long fileId);
}