package com.gientech.ragindexservice.domain.mapper;

import com.gientech.ragindexservice.domain.model.ReEmbeddingFileDO;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Param;

/**
* @author shirleychen
* @description 针对表【re_embedding_file】的数据库操作Mapper
* @createDate 2025-12-12 16:51:38
* @Entity com.gientech.ragindexservice.domain.model.ReEmbeddingFile
*/
public interface ReEmbeddingFileMapper extends BaseMapper<ReEmbeddingFileDO> {
    int getNonProcessedFileCount(@Param("taskId") Long taskId, @Param("kbId") Long kbId);
}




