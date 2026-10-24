package com.gientech.ragqaservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.gientech.ragcommon.infrastructure.exception.DomainException;
import com.gientech.ragqaservice.domain.entity.Answer;
import com.gientech.ragqaservice.domain.entity.History;
import com.gientech.ragqaservice.domain.entity.Question;
import com.gientech.ragqaservice.domain.mapper.AnswerMapper;
import com.gientech.ragqaservice.domain.model.AnswerDO;
import com.gientech.ragqaservice.domain.model.QuestionDO;
import com.gientech.ragqaservice.domain.repository.AnswerRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;

import java.util.Date;
import java.util.List;

@Repository
public class AnswerRepositoryImpl implements AnswerRepository {

    @Autowired
    private AnswerMapper answerMapper;

    @Override
    public Boolean addAnswer(Answer answer) {
        answer.setGmtModified(new Date());
        answer.setGmtCreate(new Date());
        return answerMapper.insert(BeanUtil.copyProperties(answer, AnswerDO.class)) > 0;
    }

    @Override
    public Answer getAnswerById(Long id) {
        if (id == null) {
            return null;
        }
        return BeanUtil.copyProperties(answerMapper.selectById(id), Answer.class);
    }

    @Override
    public Boolean deleteAnswerById(Long id) {
        if (id == null) {
            return false;
        }
        return answerMapper.deleteById(id) > 0;
    }

    @Override
    public Boolean updateDialogueById(Answer answer) {
        Long id = answer.getId();
        if (id == null) {
            return false;
        }
        answer.setGmtModified(new Date());
        return answerMapper.updateById(BeanUtil.copyProperties(answer, AnswerDO.class)) > 0;
    }

    @Override
    public Answer getAnswerByDialogueIdAndQuestionId(Long dialogueId,Long questionId) {
        QueryWrapper<AnswerDO> wrapper = new QueryWrapper<>();
        wrapper.lambda().eq(AnswerDO::getDialogueId,dialogueId).eq(AnswerDO::getQuestionId,questionId).last("limit 1");
        AnswerDO answerDO = answerMapper.selectOne(wrapper);
        if(answerDO !=null ){
            return BeanUtil.copyProperties(answerDO,Answer.class);
        }else{
            return null;
        }
    }

    @Override
    public List<Answer> getAnswerListByDialogueId(Long dialogueId) {
        QueryWrapper<AnswerDO> wrapper = new QueryWrapper<>();
        wrapper.lambda().eq(AnswerDO::getDialogueId,dialogueId).orderByAsc(AnswerDO::getGmtCreate);
        List<AnswerDO> answerDOList = answerMapper.selectList(wrapper);
        return BeanUtil.copyToList(answerDOList, Answer.class);
    }

    @Override
    public Long getAnswerIdByQueryId(String queryId) {
        return answerMapper.getAnswerIdByQueryId(queryId);
    }

    @Override
    public Answer getAnswerByQueryId(String queryId) {
        return BeanUtil.copyProperties(answerMapper.getAnswerByQueryId(queryId),Answer.class);
    }
}
