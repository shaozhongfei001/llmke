package com.gientech.ragqaservice.domain.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.gientech.ragqaservice.domain.model.AnswerDO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/**
 * <p>
 * 答案表 Mapper 接口
 * </p>
 *
 * @author wudf
 * @since 2024-05-08
 */
@Mapper
public interface AnswerMapper extends BaseMapper<AnswerDO> {

    Long getAnswerIdByQueryId(@Param("queryId") String queryId);

    AnswerDO getAnswerByQueryId(@Param("queryId") String queryId);

}
