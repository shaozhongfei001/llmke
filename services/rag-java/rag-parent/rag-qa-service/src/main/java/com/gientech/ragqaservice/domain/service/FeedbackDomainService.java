package com.gientech.ragqaservice.domain.service;


import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.qa.request.FeedbackQueryReq;
import com.gientech.ragqaservice.domain.entity.ConfigNameAndAnswerId;
import com.gientech.ragqaservice.domain.entity.Feedback;

import java.util.List;

/**
 * <p>
 * 反馈表 服务类
 * </p>
 *
 * @author wudf
 * @since 2024-07-18
 */
public interface FeedbackDomainService {

    Feedback findByAnswerIdAndUser(Long answerId, String userName);

    Boolean addFeedback(Feedback feedback);

    Boolean updateById(Feedback feedback);

    Boolean deleteById(Long id);

    List<Feedback> findByIds(List<Long> answerIds);

    Page<Feedback> list(List<FeedbackQueryReq.Key> keyList, String startTime, String endTime, String fuzzy, Long pageNo, Long pageSize);

    Boolean deleteByAnswerId(Long answerId);

    List<ConfigNameAndAnswerId> inAnswerIdsBySearchConfigNames(List answerIds);
}
