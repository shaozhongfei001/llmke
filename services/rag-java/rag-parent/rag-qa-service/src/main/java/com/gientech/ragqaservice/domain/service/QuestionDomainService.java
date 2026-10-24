package com.gientech.ragqaservice.domain.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.gientech.ragcommon.infrastructure.exception.DomainException;
import com.gientech.ragqaservice.domain.entity.History;
import com.gientech.ragqaservice.domain.entity.Question;
import com.gientech.ragqaservice.domain.model.QuestionDO;

import java.util.List;

/**
 * <p>
 * 问题表 服务类
 * </p>
 *
 * @author wudf
 * @since 2024-05-08
 */
public interface QuestionDomainService extends IService<QuestionDO> {

    Long addQuestion(Question question) throws DomainException;

    Question getQuestionById(Long id) throws DomainException;

    Boolean deleteQuestionById(Long id) throws DomainException;

    Long updateQuestionById(Question question) throws DomainException;

    Long addOrUpdateQuestionByDialogueIdAndFrontUuid(Question question) throws DomainException;

    List<History> getHistoryListByDialogueId(Long dialogueId, Long answerId, String orderByName, Integer count);

    List<Question> getQuestionListByDialogueId(Long dialogueId);
}
