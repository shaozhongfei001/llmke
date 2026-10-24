package com.gientech.ragqaservice.domain.service.impl;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.qa.request.FeedbackQueryReq;
import com.gientech.ragqaservice.domain.entity.ConfigNameAndAnswerId;
import com.gientech.ragqaservice.domain.entity.Feedback;
import com.gientech.ragqaservice.domain.repository.FeedbackRepository;
import com.gientech.ragqaservice.domain.service.FeedbackDomainService;
import org.apache.commons.compress.utils.Lists;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;
import java.util.Date;
import java.util.List;

/**
 * <p>
 * 反馈表 服务实现类
 * </p>
 *
 * @author wudf
 * @since 2024-07-18
 */
@Service
public class FeedbackDomainServiceImpl implements FeedbackDomainService {

    @Autowired
    private FeedbackRepository feedbackRepository;

    @Override
    public Feedback findByAnswerIdAndUser(Long answerId, String userName) {
        return feedbackRepository.findByAnswerIdAndUser(answerId,userName);
    }

    @Override
    public Boolean addFeedback(Feedback feedback) {
        return feedbackRepository.addFeedback(feedback);
    }

    @Override
    public Boolean updateById(Feedback feedback) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        feedback.setUserName(userName);
        feedback.setUpdateBy(userName);
        feedback.setGmtModified(new Date());
        return feedbackRepository.updateById(feedback);
    }

    @Override
    public Boolean deleteById(Long id) {
        return feedbackRepository.deleteById(id);
    }

    @Override
    public List<Feedback> findByIds(List<Long> answerIds) {
        List<Feedback> feedbacks = feedbackRepository.findByIds(answerIds);
        return CollectionUtils.isEmpty(feedbacks) ? Lists.newArrayList() : feedbacks;
    }

    @Override
    public Page<Feedback> list(List<FeedbackQueryReq.Key> keyList,String startTime, String endTime, String fuzzy, Long pageNo, Long pageSize) {
        return feedbackRepository.list(keyList,startTime,endTime,fuzzy,pageNo,pageSize);
    }

    @Override
    public Boolean deleteByAnswerId(Long answerId) {
        return feedbackRepository.deleteByAnswerId(answerId);
    }


    @Override
    public List<ConfigNameAndAnswerId> inAnswerIdsBySearchConfigNames(List answerIds) {
        return feedbackRepository.inAnswerIdsBySearchConfigNames(answerIds);
    }
}
