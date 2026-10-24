package com.gientech.ragqaservice.domain.repository;


import com.gientech.ragqaservice.domain.entity.Answer;
import org.apache.ibatis.annotations.Param;

import java.util.List;

public interface AnswerRepository {

    Boolean addAnswer(Answer answer);

    Answer getAnswerById(Long id);

    Boolean deleteAnswerById(Long id);

    Boolean updateDialogueById(Answer answer);

    Answer getAnswerByDialogueIdAndQuestionId(Long dialogueId,Long questionId);

    List<Answer> getAnswerListByDialogueId(Long dialogueId);

    Long getAnswerIdByQueryId(String queryId);

    Answer getAnswerByQueryId(String queryId);
}
