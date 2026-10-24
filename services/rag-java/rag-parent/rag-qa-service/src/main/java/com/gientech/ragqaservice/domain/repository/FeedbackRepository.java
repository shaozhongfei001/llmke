package com.gientech.ragqaservice.domain.repository;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.qa.request.FeedbackQueryReq;
import com.gientech.ragqaservice.domain.entity.ConfigNameAndAnswerId;
import com.gientech.ragqaservice.domain.entity.Feedback;
import java.util.List;

public interface FeedbackRepository {

    Feedback findByAnswerIdAndUser(Long answerId, String userName);

    Boolean addFeedback(Feedback feedback);

    Boolean updateById(Feedback feedback);

    Boolean deleteById(Long id);

    List<Feedback> findByIds(List<Long> answerIds);

    Page<Feedback> list(List<FeedbackQueryReq.Key> keyList,String startTime, String endTime, String fuzzy, Long pageNo, Long pageSize);

    Boolean deleteByAnswerId(Long answerId);

    List<ConfigNameAndAnswerId> inAnswerIdsBySearchConfigNames(List answerIds);
}
