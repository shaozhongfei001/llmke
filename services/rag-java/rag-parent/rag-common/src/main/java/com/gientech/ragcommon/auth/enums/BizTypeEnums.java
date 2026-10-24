package com.gientech.ragcommon.auth.enums;

import com.fasterxml.jackson.annotation.JsonValue;
import lombok.Getter;

import java.util.Objects;

@Getter
public enum BizTypeEnums {

    KNOWLEDGE_BASE(1, "知识库"),
    INDEX_CONF(2, "问答助手"),
    MODEL(3, "模型"),
    KNOWLEDGE_BASE_FILE(4, "知识库文件"),
    FOLDER(6, "知识库文件-文件夹"),
    FAQ(7, "faq"),
    FAQ_FOLDER(8, "faq文件夹-管理"),
    FAQ_FILE(10, "faq关联的文件-管理"),
    FAQ_EXTRACT_FOLDER(9, "faq文件夹-抽取"),
    FAQ_EXTRACT_FILE(11, "faq关联的文件-抽取"),
    DATABASE(12, "数据库");


    @JsonValue
    private Integer code;
    private String desc;

    BizTypeEnums(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }

    public static BizTypeEnums of(Integer code) {
        for (BizTypeEnums item : BizTypeEnums.values()) {
            if (item.getCode().equals(code)) {
                return item;
            }
        }
        return null;
    }

    public static boolean isFolderType(Integer code) {
        BizTypeEnums bizTypeEnums = of(code);
        return Objects.nonNull(bizTypeEnums) && (bizTypeEnums.equals(FOLDER) || bizTypeEnums.equals(FAQ_FOLDER) || bizTypeEnums.equals(FAQ_EXTRACT_FOLDER));
    }

    public static boolean isFaqFolder(Integer code) {
        BizTypeEnums bizTypeEnums = of(code);
        return Objects.nonNull(bizTypeEnums) && (bizTypeEnums.equals(FAQ_FOLDER) || bizTypeEnums.equals(FAQ_EXTRACT_FOLDER) || bizTypeEnums.equals(FAQ_FILE));
    }

    public static boolean isFileType(Integer code) {
        BizTypeEnums bizTypeEnums = of(code);
        return Objects.nonNull(bizTypeEnums) && (bizTypeEnums.equals(KNOWLEDGE_BASE_FILE) || bizTypeEnums.equals(FAQ_FILE) || bizTypeEnums.equals(FAQ_EXTRACT_FILE));
    }

    public static boolean isFaq(Integer code) {
        BizTypeEnums bizTypeEnums = of(code);
        return Objects.nonNull(bizTypeEnums) && bizTypeEnums.equals(FAQ);
    }

    public static boolean isFAQExtract(BizTypeEnums bizTypeEnums) {
        return bizTypeEnums.equals(FAQ_EXTRACT_FILE) || bizTypeEnums.equals(FAQ_EXTRACT_FOLDER);
    }
}


