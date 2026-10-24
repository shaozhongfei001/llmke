package com.gientech.ragqaservice.domain.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.gientech.ragqaservice.domain.model.HistoryDO;
import com.gientech.ragqaservice.domain.model.QuestionDO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * <p>
 * 问题表 Mapper 接口
 * </p>
 *
 * @author wudf
 * @since 2024-05-08
 */
@Mapper
public interface QuestionMapper extends BaseMapper<QuestionDO> {
    List<HistoryDO> getHistoryListByDialogueId(@Param("dialogueId") Long dialogueId,@Param("answerId") Long answerId,@Param("orderByName") String orderByName, @Param("count") Integer count);
}
