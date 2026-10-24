package com.gientech.ragqaservice.domain.repository;

import com.gientech.ragqaservice.domain.entity.History;
import com.gientech.ragqaservice.domain.entity.Question;
import java.util.List;

public interface QuestionRepository {

    Long addQuestion(Question question);

    Question getQuestionById(Long id);

    Boolean deleteQuestionById(Long id);

    Long updateQuestionById(Question question);

    Question getQuestionByDialogueIdAndFrontUuid(Long dialogueId,String frontUuid);

    List<History> getHistoryListByDialogueId(Long dialogueId, Long answerId, String orderByName, Integer count);

    List<Question> getQuestionListByDialogueId(Long dialogueId);
}
