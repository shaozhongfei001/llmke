package com.gientech.ragindexservice.domain.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.gientech.ragindexservice.domain.model.ReEmbeddingRetryTaskDO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/**
 * @author shirleychen
 * @description 针对表【re_embedding_retry_task】的数据库操作Mapper
 * @createDate 2025-11-28 14:35:41
 * @Entity com.gientech.ragindexservice.domain.model.ReEmbeddingRetryTask
 */
@Mapper
public interface ReEmbeddingRetryTaskMapper extends BaseMapper<ReEmbeddingRetryTaskDO> {

    int findExistTaskByFileId(@Param("taskId") Long taskId, @Param("fileId") Long fileId);
}




