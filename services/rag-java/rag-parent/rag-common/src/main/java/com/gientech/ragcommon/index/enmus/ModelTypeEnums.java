package com.gientech.ragcommon.index.enmus;

import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import lombok.Getter;

import java.util.Objects;

/**
 * 模型使用类型
 */
@Getter
public enum ModelTypeEnums {
    // 1:LLM大语言模型、2:Embedding嵌入、3:rerank排序、4:MultiModel图片解析

    LLM(1,"LLM大语言模型","modelName"),
    EMBEDDING(2,"Embedding嵌入","embeddingModelName"),
    RERANK(3,"rerank排序","rerankModelName"),
    MULTI_MODEL(4,"MultiModel图片解析","multiModelName"),
    ;


    private final Integer code;
    private final String desc;
    private final String fieldName;

    ModelTypeEnums(Integer code, String statusMsg, String fieldName) {
        this.code = code;
        this.desc = statusMsg;
        this.fieldName = fieldName;
    }

    public static ModelTypeEnums getByCode(Integer type){
        ModelTypeEnums[] values = ModelTypeEnums.values();
        for (ModelTypeEnums value : values) {
            if (value.getCode().equals(type)) {
                return value;
            }
        }
        return null;
    }
}
