package com.gientech.ragqaservice.domain.mapper;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.core.toolkit.Constants;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragqaservice.domain.model.ConfigNameAndAnswerIdDO;
import com.gientech.ragqaservice.domain.model.FeedbackDO;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import com.baomidou.mybatisplus.core.conditions.Wrapper;
/**
 * <p>
 * 反馈表 Mapper 接口
 * </p>
 *
 * @author wudf
 * @since 2024-07-18
 */
@Mapper
public interface FeedbackMapper extends BaseMapper<FeedbackDO> {

    int updateInfoById(@Param("item") FeedbackDO feedbackDO);

    List<ConfigNameAndAnswerIdDO> inAnswerIdsBySearchConfigNames(@Param("answerIds") List answerIds);

    Page<FeedbackDO> selectPageCustom(IPage<FeedbackDO> page, @Param(Constants.WRAPPER) Wrapper<FeedbackDO> queryWrapper);
}
