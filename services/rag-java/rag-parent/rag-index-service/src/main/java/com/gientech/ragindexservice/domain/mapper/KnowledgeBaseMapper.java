package com.gientech.ragindexservice.domain.mapper;

import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragindexservice.domain.model.KnowledgeBaseDO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * <p>
 * 知识库 Mapper 接口
 * </p>
 *
 * @author wudf
 * @since 2024-06-04
 */
@Mapper
public interface KnowledgeBaseMapper extends BaseMapper<KnowledgeBaseDO> {

    Integer getHighestPermission(@Param("kbId") Long kbId, @Param("deptId") Long deptId, @Param("userId") Long userId, @Param("userName") String userName);

    int updateCreator(@Param("ids") List<Long> ids, @Param("userName") String userName);

    int replaceModel(@Param("sourceModelName")String sourceModelName, @Param("targetModelName")String targetModelName);

    List<KnowledgeBaseDO> selectUseSpecifiedModelKbList(@Param("modelTypeName") String modelTypeName, @Param("modelName") String modelName);

    int selectReferenceByModelName(@Param("modelName") String modelName);
}
