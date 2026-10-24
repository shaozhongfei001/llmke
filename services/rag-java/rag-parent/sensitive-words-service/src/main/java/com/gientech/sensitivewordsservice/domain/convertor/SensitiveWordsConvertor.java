package com.gientech.sensitivewordsservice.domain.convertor;

import com.gientech.ragcommon.sensitive.dto.SensitiveWordsDTO;
import com.gientech.sensitivewordsservice.domain.entity.SensitiveWords;
import com.gientech.sensitivewordsservice.domain.model.SensitiveWordsDO;
import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;

import java.util.List;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/8/28 11:24
 */
@Mapper
public interface SensitiveWordsConvertor {
    SensitiveWordsConvertor INSTANCE = Mappers.getMapper(SensitiveWordsConvertor.class);


    List<SensitiveWords> wordsDOList2WordsList(List<SensitiveWordsDO> wordsDOList);

    List<SensitiveWordsDTO> wordsList2WordsDTOList(List<SensitiveWords> wordsList);

    SensitiveWords sensitiveWordsDO2SensitiveWords(SensitiveWordsDO sensitiveWordsDO);
}
