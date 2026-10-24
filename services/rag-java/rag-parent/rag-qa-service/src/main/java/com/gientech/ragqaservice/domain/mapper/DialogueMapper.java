package com.gientech.ragqaservice.domain.mapper;

import com.gientech.ragqaservice.domain.model.DbIdDO;
import com.gientech.ragqaservice.domain.model.DialogueDO;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * <p>
 * 对话表 Mapper 接口
 * </p>
 *
 * @author wudf
 * @since 2024-06-24
 */
@Mapper
public interface DialogueMapper extends BaseMapper<DialogueDO> {

    List<DbIdDO> getIdsBySessionIdAndQueryId(@Param("sessionId") String sessionId, @Param("queryId") String queryId);
}
