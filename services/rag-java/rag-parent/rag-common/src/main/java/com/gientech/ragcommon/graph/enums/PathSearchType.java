package com.gientech.ragcommon.graph.enums;

import lombok.Getter;

import java.util.Objects;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2023/3/20 22:15
 */
public enum PathSearchType {
    ALL(1,"ALL"),
    SHORTEST(2,"SHORTEST"),
    NOLOOP(3,"NOLOOP");

    @Getter
    private Integer value;
    @Getter
    private String type;

    PathSearchType(Integer value, String type){
        this.value = value;
        this.type = type;
    }
    public static PathSearchType of(Integer value){
        if(Objects.isNull(value)){
            return null;
        }
        for (PathSearchType pathSearchType : PathSearchType.values()) {
            if(Objects.equals(value, pathSearchType.getValue())){
                return pathSearchType;
            }
        }
        return null;
    }
}
