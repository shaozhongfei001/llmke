package com.gientech.ragcommon.index.enmus;

import lombok.Getter;

@Getter
public enum SearchConfigScopeEnums {
    SHARE("share", "共享助手"),
    ALL("all", "我的和共享助手"),
    OWN("own", "我的助手");

    private final String value;
    private final String desc;

    SearchConfigScopeEnums(String value, String desc) {
        this.value = value;
        this.desc = desc;
    }

    public static SearchConfigScopeEnums of(String value) {
        for (SearchConfigScopeEnums e : SearchConfigScopeEnums.values()) {
            if (e.value.equals(value)) {
                return e;
            }
        }
        return null;
    }
}
