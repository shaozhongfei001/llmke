package com.gientech.ragqaservice.domain.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.gientech.ragcommon.infrastructure.exception.DomainException;
import com.gientech.ragqaservice.domain.entity.Answer;
import com.gientech.ragqaservice.domain.model.AnswerDO;

import java.util.List;

/**
 * <p>
 * 答案表 服务类
 * </p>
 *
 * @author wudf
 * @since 2024-05-08
 */
public interface AnswerDomainService extends IService<AnswerDO> {

    Boolean addAnswer(Answer answer);

    Answer getAnswerById(Long id);

    Boolean deleteAnswerById(Long id);

    Boolean updateDialogueById(Answer answer);

    Boolean addOrUpdateAnswerByDialogueIdAndQuestionId(Answer answer) throws DomainException;

    List<Answer> getAnswerListByDialogueId(Long dialogueId);

    Answer getAnswerByDialogueIdAndQuestionId(Long dialogueId,Long questionId);

    Long getAnswerIdByQueryId(String queryId);

    Answer getAnswerByQueryId(String queryId);
}
