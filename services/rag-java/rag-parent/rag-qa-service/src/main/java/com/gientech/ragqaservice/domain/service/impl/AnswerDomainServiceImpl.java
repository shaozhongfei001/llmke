package com.gientech.ragqaservice.domain.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.gientech.ragcommon.infrastructure.exception.DomainException;
import com.gientech.ragqaservice.domain.entity.Answer;
import com.gientech.ragqaservice.domain.mapper.AnswerMapper;
import com.gientech.ragqaservice.domain.model.AnswerDO;
import com.gientech.ragqaservice.domain.repository.AnswerRepository;
import com.gientech.ragqaservice.domain.service.AnswerDomainService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * <p>
 * 答案表 服务实现类
 * </p>
 *
 * @author wudf
 * @since 2024-05-08
 */
@Service
public class AnswerDomainServiceImpl extends ServiceImpl<AnswerMapper, AnswerDO> implements AnswerDomainService {

    @Autowired
    private AnswerRepository answerRepository;

    @Override
    public Boolean addAnswer(Answer answer) {
        return answerRepository.addAnswer(answer);
    }

    @Override
    public Answer getAnswerById(Long id) {
        return answerRepository.getAnswerById(id);
    }

    @Override
    public Boolean deleteAnswerById(Long id) {
        return answerRepository.deleteAnswerById(id);
    }

    @Override
    public Boolean updateDialogueById(Answer answer) {
        return answerRepository.updateDialogueById(answer);
    }

    @Override
    public Boolean addOrUpdateAnswerByDialogueIdAndQuestionId(Answer answer) throws DomainException {
        Answer dbAnswer = answerRepository.getAnswerByDialogueIdAndQuestionId(answer.getDialogueId(),answer.getQuestionId());
        Boolean flag ;
        if(dbAnswer == null){
            flag = addAnswer(answer);
        }else{
            answer.setId(dbAnswer.getId());
            flag = updateDialogueById(answer);
        }
        return flag;
    }

    @Override
    public List<Answer> getAnswerListByDialogueId(Long dialogueId) {
        return answerRepository.getAnswerListByDialogueId(dialogueId);
    }

    @Override
    public Answer getAnswerByDialogueIdAndQuestionId(Long dialogueId, Long questionId) {
        return answerRepository.getAnswerByDialogueIdAndQuestionId(dialogueId,questionId);
    }

    @Override
    public Long getAnswerIdByQueryId(String queryId) {
        return answerRepository.getAnswerIdByQueryId(queryId);
    }

    @Override
    public Answer getAnswerByQueryId(String queryId) {
        return answerRepository.getAnswerByQueryId(queryId);
    }
}
