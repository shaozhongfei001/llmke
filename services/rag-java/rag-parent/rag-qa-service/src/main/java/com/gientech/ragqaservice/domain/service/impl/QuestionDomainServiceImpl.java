package com.gientech.ragqaservice.domain.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.gientech.ragcommon.infrastructure.exception.DomainException;
import com.gientech.ragqaservice.domain.entity.Dialogue;
import com.gientech.ragqaservice.domain.entity.History;
import com.gientech.ragqaservice.domain.entity.Question;
import com.gientech.ragqaservice.domain.mapper.QuestionMapper;
import com.gientech.ragqaservice.domain.model.QuestionDO;
import com.gientech.ragqaservice.domain.repository.QuestionRepository;
import com.gientech.ragqaservice.domain.service.QuestionDomainService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * <p>
 * 问题表 服务实现类
 * </p>
 *
 * @author wudf
 * @since 2024-05-08
 */
@Service
public class QuestionDomainServiceImpl extends ServiceImpl<QuestionMapper, QuestionDO> implements QuestionDomainService {

    @Autowired
    private QuestionRepository questionRepository;
    @Override
    public Long addQuestion(Question question) throws DomainException {
        return questionRepository.addQuestion(question);
    }

    @Override
    public Question getQuestionById(Long id) throws DomainException {
        return questionRepository.getQuestionById(id);
    }

    @Override
    public Boolean deleteQuestionById(Long id) throws DomainException {
        return questionRepository.deleteQuestionById(id);
    }

    @Override
    public Long updateQuestionById(Question question) throws DomainException {
        return questionRepository.updateQuestionById(question);
    }

    @Override
    public Long addOrUpdateQuestionByDialogueIdAndFrontUuid(Question question) throws DomainException {
        Question dbQuestion = questionRepository.getQuestionByDialogueIdAndFrontUuid(question.getDialogueId(),question.getFrontUuid());
        Long id ;
        if(dbQuestion == null){
            id = addQuestion(question);
        }else{
            question.setId(dbQuestion.getId());
            id = updateQuestionById(question);
        }
        return id;
    }

    @Override
    public List<History> getHistoryListByDialogueId(Long dialogueId, Long answerId, String orderByName, Integer count) {
        return questionRepository.getHistoryListByDialogueId(dialogueId,answerId,orderByName,count);
    }

    @Override
    public List<Question> getQuestionListByDialogueId(Long dialogueId) {
        return questionRepository.getQuestionListByDialogueId(dialogueId);
    }
}
