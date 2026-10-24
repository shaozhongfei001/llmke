package com.gientech.ragqaservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.gientech.ragcommon.infrastructure.exception.DomainException;
import com.gientech.ragqaservice.domain.entity.Answer;
import com.gientech.ragqaservice.domain.entity.Dialogue;
import com.gientech.ragqaservice.domain.entity.History;
import com.gientech.ragqaservice.domain.entity.Question;
import com.gientech.ragqaservice.domain.mapper.QuestionMapper;
import com.gientech.ragqaservice.domain.model.AnswerDO;
import com.gientech.ragqaservice.domain.model.DialogueDO;
import com.gientech.ragqaservice.domain.model.HistoryDO;
import com.gientech.ragqaservice.domain.model.QuestionDO;
import com.gientech.ragqaservice.domain.repository.QuestionRepository;
import org.apache.ibatis.annotations.Param;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;

@Repository
public class QuestionRepositoryImpl implements QuestionRepository {

    @Autowired
    private QuestionMapper questionMapper;

    @Override
    public Long addQuestion(Question question) {
        Date date = new Date();
        question.setGmtCreate(date);
        question.setGmtModified(date);
        QuestionDO questionDO = BeanUtil.copyProperties(question, QuestionDO.class);
        questionMapper.insert(questionDO);
        return questionDO.getId();
    }

    @Override
    public Question getQuestionById(Long id) {
        if(id == null){
            return null;
        }
        return BeanUtil.copyProperties(questionMapper.selectById(id),Question.class);
    }

    @Override
    public Boolean deleteQuestionById(Long id) {
        if(id == null){
            return false;
        }
        return questionMapper.deleteById(id)>0;
    }

    @Override
    public Long updateQuestionById(Question question) {
        Long id = question.getId();
        if(id == null){
            return -1L;
        }
        question.setGmtModified(new Date());
        questionMapper.updateById(BeanUtil.copyProperties(question, QuestionDO.class));
        return id;
    }

    @Override
    public Question getQuestionByDialogueIdAndFrontUuid(Long dialogueId,String frontUuid) throws DomainException {
        QueryWrapper<QuestionDO> wrapper = new QueryWrapper<>();
        wrapper.lambda().eq(QuestionDO::getDialogueId,dialogueId).eq(QuestionDO::getFrontUuid,frontUuid).last("limit 1");
        QuestionDO questionDO = questionMapper.selectOne(wrapper);
        if(questionDO !=null ){
            return BeanUtil.copyProperties(questionDO,Question.class);
        }else{
            return null;
        }
    }

    @Override
    public List<History> getHistoryListByDialogueId(Long dialogueId, Long answerId, String orderByName, Integer count) {
        List<HistoryDO> historyDOList = questionMapper.getHistoryListByDialogueId(dialogueId,answerId,orderByName,count);
        return BeanUtil.copyToList(historyDOList,History.class);
    }

    @Override
    public List<Question> getQuestionListByDialogueId(Long dialogueId) {
        QueryWrapper<QuestionDO> wrapper = new QueryWrapper<>();
        wrapper.lambda().eq(QuestionDO::getDialogueId,dialogueId).orderByAsc(QuestionDO::getGmtCreate);
        List<QuestionDO> questionDOList = questionMapper.selectList(wrapper);
        return BeanUtil.copyToList(questionDOList, Question.class);
    }
}
