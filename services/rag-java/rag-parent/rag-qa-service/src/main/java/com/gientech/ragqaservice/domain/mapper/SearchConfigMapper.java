package com.gientech.ragqaservice.domain.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.gientech.ragqaservice.domain.model.SearchConfigDO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * <p>
 * 问题查询配置表 Mapper 接口
 * </p>
 *
 * @author wudf
 * @since 2024-11-14
 */
@Mapper
public interface SearchConfigMapper extends BaseMapper<SearchConfigDO> {
    int updateSensitiveWord(String wordId);

    int updateKnowledgeBase(String baseName);

    int updateSourceKnowledgeBase(String sourceName);

    int updateKbSourceName(@Param("sourceName") String sourceName, @Param("targetName") String targetName);

    int updateDbIndex(@Param("dbIndex")String dbIndex);

    int renameDbIndex(@Param("dbKey")String dbKey, @Param("newDbLabel") String newDbLabel, @Param("oldDbLabel") String oldDbLabel);

    int updateTrace(@Param("modelName") String modelName, @Param("needTrace") Boolean needTrace);

    int updateModelConfig(@Param("modelName") String modelName, @Param("thinking") Boolean thinking);

    int updateCreator(@Param("ids") List<Long> ids, @Param("userName") String userName, @Param("isClearKb") boolean isClearKb);

    int replaceModelName(@Param("sourceModelName") String sourceModelName, @Param("targetModelName") String targetModelName);

    int selectReferenceByModelName(@Param("modelName") String modelName);
}
