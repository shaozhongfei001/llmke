package com.gientech.ragqaservice.domain.conventer;

import com.gientech.ragqaservice.domain.entity.ExtendedConfig;
import com.gientech.ragqaservice.domain.entity.Question;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;
import org.mapstruct.factory.Mappers;

import java.util.Objects;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/9/27 11:24
 */
@Mapper
public interface QuestionConvertor {
    QuestionConvertor INSTANCE = Mappers.getMapper(QuestionConvertor.class);

    default Question extendedConfig2Question(ExtendedConfig config) {
        if (config == null) {
            return null;
        }

        Question question = new Question();

        question.setKnowledgeBaseName(config.getKnowledgeBaseName());

        return question;
    }
}
