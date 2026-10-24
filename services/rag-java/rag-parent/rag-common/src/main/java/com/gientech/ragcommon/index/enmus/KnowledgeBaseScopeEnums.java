package com.gientech.ragcommon.index.enmus;

import lombok.Getter;

public enum KnowledgeBaseScopeEnums {
    SHARE("share", "共享知识库"),
    ALL("all", "我的和共享知识库"),
    OWN("own", "我的知识库");

    @Getter
    private String value;
    @Getter
    private String desc;

    KnowledgeBaseScopeEnums(String value, String desc) {
        this.value = value;
        this.desc = desc;
    }

    public static KnowledgeBaseScopeEnums of(String value) {
        for (KnowledgeBaseScopeEnums knowledgeBaseScopeEnums : KnowledgeBaseScopeEnums.values()) {
            if (knowledgeBaseScopeEnums.value.equals(value)) {
                return knowledgeBaseScopeEnums;
            }
        }
        return null;
    }
}
