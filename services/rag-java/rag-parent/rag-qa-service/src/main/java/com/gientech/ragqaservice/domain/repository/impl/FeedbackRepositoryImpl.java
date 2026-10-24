package com.gientech.ragqaservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollectionUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.index.enmus.IsDelEnums;
import com.gientech.ragcommon.qa.enmus.FeedbackResultEnums;
import com.gientech.ragcommon.qa.request.FeedbackQueryReq;
import com.gientech.ragqaservice.domain.entity.ConfigNameAndAnswerId;
import com.gientech.ragqaservice.domain.entity.Feedback;
import com.gientech.ragqaservice.domain.mapper.FeedbackMapper;
import com.gientech.ragqaservice.domain.model.ConfigNameAndAnswerIdDO;
import com.gientech.ragqaservice.domain.model.FeedbackDO;
import com.gientech.ragqaservice.domain.repository.FeedbackRepository;
import com.google.common.collect.Maps;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import org.springframework.util.CollectionUtils;

import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.Objects;

@Repository
public class FeedbackRepositoryImpl implements FeedbackRepository {

    @Autowired
    private FeedbackMapper feedbackMapper;

    @Override
    public Feedback findByAnswerIdAndUser(Long answerId, String userName) {
        QueryWrapper<FeedbackDO> queryWrapper = new QueryWrapper<>();
        queryWrapper
                .eq("is_del",IsDelEnums.NORMAL.getCode())
                .eq("answer_id", answerId)
                .eq("create_by", userName)
                .last("limit 1");
        FeedbackDO feedbackDO = feedbackMapper.selectOne(queryWrapper);
        return Objects.isNull(feedbackDO) ? null : BeanUtil.copyProperties(feedbackDO, Feedback.class);
    }

    @Override
    public Boolean addFeedback(Feedback feedback) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        feedback.setUserName(userName);
        feedback.setCreateBy(userName);
        feedback.setUpdateBy(userName);
        feedback.setGmtCreate(new Date());
        feedback.setGmtModified(feedback.getGmtCreate());
        return feedbackMapper.insert(BeanUtil.copyProperties(feedback, FeedbackDO.class)) > 0;
    }

    @Override
    public Boolean updateById(Feedback feedback) {
        return feedbackMapper.updateInfoById(BeanUtil.copyProperties(feedback, FeedbackDO.class)) > 0;
    }

    @Override
    public Boolean deleteById(Long id) {
        QueryWrapper<FeedbackDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("id", id);

        FeedbackDO feedbackDO = new FeedbackDO();
        feedbackDO.setAnswerId(id);
        feedbackDO.setGmtModified(new Date());
        feedbackDO.setIsDel(IsDelEnums.DELETE.getCode());
        return feedbackMapper.update(feedbackDO,queryWrapper) > 0;
    }

    @Override
    public List<Feedback> findByIds(List<Long> answerIds) {
        if (CollectionUtil.isEmpty(answerIds)) {
            return null;
        }
        User user = UserContext.getUser();
        String userName = user.getUserName();
        QueryWrapper<FeedbackDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.in("answer_id", answerIds)
                .eq("create_by", userName)
                .eq("is_del",IsDelEnums.NORMAL.getCode());
        List<FeedbackDO> feedbackDOS = feedbackMapper.selectList(queryWrapper);
        return CollectionUtil.isEmpty(feedbackDOS) ? null : BeanUtil.copyToList(feedbackDOS, Feedback.class);
    }

    @Override
    public Page<Feedback> list(List<FeedbackQueryReq.Key> keyList, String startTime, String endTime, String fuzzy, Long pageNo, Long pageSize) {
        QueryWrapper<FeedbackDO> queryWrapper = new QueryWrapper<>();
        Page<FeedbackDO> page = new Page<>(pageNo, pageSize);
        queryWrapper.eq("is_del",IsDelEnums.NORMAL.getCode())
                .eq("restult", FeedbackResultEnums.NU_LIKE.getCode());
        if (!CollectionUtils.isEmpty(keyList)) {
            Map<String, Object> keyMap = Maps.newHashMap();
            keyList.forEach(key -> keyMap.put(key.getColumn(), key.getColumnValue()));
            queryWrapper.and(
                    queError -> queError.like("t1.que_error", keyMap.get("que_error"))
                            .or(ansPoor -> ansPoor.like("t1.ans_poor", keyMap.get("ans_poor")))
                            .or(formatError -> formatError.like("t1.format_error", keyMap.get("format_error")))
                            .or(formatError -> formatError.like("t1.harmful_info", keyMap.get("harmful_info")))
                            .or(formatError -> formatError.like("t1.othres", keyMap.get("othres")))
            );
        }
        if (StringUtils.isNotBlank(fuzzy))
            queryWrapper.and(
//                    queError -> queError.like("que_error", fuzzy)
//                            .or(ansPoor -> ansPoor.like("ans_poor", fuzzy))
//                            .or(formatError -> formatError.like("format_error", fuzzy))
//                            .or(harmfulInfo -> harmfulInfo.like("harmful_info", fuzzy))
//                            .or(formatError -> formatError.like("othres", fuzzy))
                    answer -> answer.like("t2.content", fuzzy)
                            .or(question->question.like("t3.content", fuzzy))
                            .or(userName -> userName.like("t1.user_name", fuzzy))
            );
        if (StringUtils.isNotBlank(startTime) && StringUtils.isNotBlank(endTime))
            queryWrapper.between("t1.gmt_create", startTime + " 00:00:00", endTime + " 23:59:59");
        queryWrapper.orderByDesc("t1.gmt_create");
        Page<FeedbackDO> pageResult = feedbackMapper.selectPageCustom(page, queryWrapper);
        Page<Feedback> feedbackPage = new Page<>();
        BeanUtil.copyProperties(pageResult, feedbackPage);
        feedbackPage.setRecords(BeanUtil.copyToList(pageResult.getRecords(), Feedback.class));
        return feedbackPage;
    }

    @Override
    public Boolean deleteByAnswerId(Long answerId) {
        if (Objects.isNull(answerId))
            return false;
        User user = UserContext.getUser();
        String userName = user.getUserName();
        QueryWrapper<FeedbackDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("answer_id", answerId)
                .eq(StringUtils.isNotBlank(userName),"create_by", userName);

        FeedbackDO feedbackDO = new FeedbackDO();
        feedbackDO.setAnswerId(answerId);
        feedbackDO.setGmtModified(new Date());
        feedbackDO.setIsDel(IsDelEnums.DELETE.getCode());
        return feedbackMapper.update(feedbackDO,queryWrapper) > 0;
    }

    @Override
    public List<ConfigNameAndAnswerId> inAnswerIdsBySearchConfigNames(List answerIds) {
        List<ConfigNameAndAnswerIdDO> ConfigNameAndAnswerIdDOs = feedbackMapper.inAnswerIdsBySearchConfigNames(answerIds);
        return CollectionUtil.isEmpty(ConfigNameAndAnswerIdDOs) ? null : BeanUtil.copyToList(ConfigNameAndAnswerIdDOs, ConfigNameAndAnswerId.class);
    }
}
