package com.gientech.ragcommon.auth.enums;

import com.fasterxml.jackson.annotation.JsonValue;

import java.util.List;
import java.util.Objects;

/**
 * 数据权限
 */
public enum PrivilegeTypeEnums {

    KNOWLEDGE_BASE(1, "知识库"),
    INDEX_CONF(2, "问答助手"),
    MODEL(3, "模型"),
    KNOWLEDGE_BASE_FILE(4, "知识库文件"),
    ARTICLE_TEMPLATE(5,"文档写作模板"),
    FOLDER(6,"文件夹"),
    FAQ(7, "faq"),
    FAQ_FOLDER(8, "faq文件夹-管理"),
    FAQ_FILE(10,"faq关联的文件-管理"),
    FAQ_EXTRACT_FOLDER(9,"faq文件夹-抽取"),
    FAQ_EXTRACT_FILE(11,"faq关联的文件-抽取"),
    DATABASE(12, "数据库");

    @JsonValue
    private Integer code;
    private String desc;

    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    PrivilegeTypeEnums(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }

    /**
     * 根据code获取枚举
     */
    public static PrivilegeTypeEnums getEnumByCode(Integer code) {
        for (PrivilegeTypeEnums privilegeTypeEnums : PrivilegeTypeEnums.values()) {
            if (privilegeTypeEnums.getCode().equals(code)) {
                return privilegeTypeEnums;
            }
        }
        return null;
    }

    public static List<PrivilegeTypeEnums> transferTypeList(List<Integer> codes) {
        return codes.stream().map(PrivilegeTypeEnums::getEnumByCode).filter(t->Objects.nonNull(t) && !t.equals(KNOWLEDGE_BASE_FILE)).toList();
    }

}
