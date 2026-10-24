package com.gientech.ragcommon.graph.enums;

import lombok.Getter;

import java.util.Objects;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2023/3/20 21:35
 */
public enum SearchDirectionEnum {
    INCOMING(1,""),
    OUTGOING(2,""),
    BIDIRECT(3,"bidirect");

    @Getter
    private Integer value;
    @Getter
    private String direction;

    SearchDirectionEnum(Integer value, String direction){
        this.value = value;
        this.direction = direction;
    }
    public static SearchDirectionEnum of(Integer value){
        if(Objects.isNull(value)){
            return null;
        }
        for (SearchDirectionEnum searchDirectionEnum : SearchDirectionEnum.values()) {
            if(Objects.equals(value, searchDirectionEnum.getValue())){
                return searchDirectionEnum;
            }
        }
        return null;
    }
}
