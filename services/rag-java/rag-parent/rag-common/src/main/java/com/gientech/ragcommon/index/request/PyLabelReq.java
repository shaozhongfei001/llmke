package com.gientech.ragcommon.index.request;

import com.fasterxml.jackson.annotation.JsonFilter;
import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.ser.FilterProvider;
import com.fasterxml.jackson.databind.ser.impl.SimpleBeanPropertyFilter;
import com.fasterxml.jackson.databind.ser.impl.SimpleFilterProvider;
import com.gientech.ragcommon.auth.enums.BizTypeEnums;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.google.common.collect.Maps;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;

import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * @author chenjuan
 * @date 2025/5/9 17:19
 */
@Data
@JsonFilter("dynamicFilter")
@Slf4j
public class PyLabelReq {
    @JsonProperty("index_name")
    private String indexName;
    @JsonProperty("file_id")
    private List<String> fileIds;
    @JsonProperty("col_name")
    private String colName;
    @JsonProperty("col_value")
    private Object colValue;
    @JsonProperty("update_condition_json")
    private Map<String, Map<String, Object>> updateConditionJson = Maps.newHashMap();
    @JsonProperty("pk")
    private List<String> pk;
    @JsonProperty("update_file_name")
    private String updateFileName;

    @JsonIgnore
    private boolean useBatch;


    public static String getReqByFolderId(String indexName, Long folderId) {
        String req = """
                {
                    "index_name": [
                        "%s"
                    ],
                    "sort_field": "update_time",
                    "sort_mode": "desc",
                    "condition_json": [
                        {"folder_id":"%s"}
                    ]
                }
                """;
        return String.format(req, indexName, folderId);
    }

    public static String getReqByFolderId(String indexName, String folderIds) {
        String req = """
                {
                    "index_name": [
                        "%s"
                    ],
                    "sort_field": "update_time",
                    "sort_mode": "desc",
                    "condition_json": [
                        {"folder_id": [%s]}
                    ]
                }
                """;
        return String.format(req, indexName, folderIds);
    }

    public static String getReqByPk(String indexName, Long pk) {
        String req = """
                {
                    "index_name": [
                        "%s"
                    ],
                    "sort_field": "update_time",
                    "sort_mode": "desc",
                    "condition_json": [
                        {"pk":"%s"}
                    ]
                }
                """;
        return String.format(req, indexName, pk);
    }

    public String getJSONString(BizTypeEnums bizTypeEnum) {
        switch (bizTypeEnum) {
            case KNOWLEDGE_BASE_FILE -> {
                return serializeWithIgnoreFields(this, Set.of("update_condition_json", "pk", "update_file_name"));
            }
            case FOLDER -> {
                return serializeWithIgnoreFields(this, Set.of("col_value", "col_name", "pk"));
            }
            case FAQ -> {
                return serializeWithIgnoreFields(this, Set.of("file_id", "update_file_name", "update_condition_json"));
            }
            case FAQ_FOLDER, FAQ_FILE -> {
                return serializeWithIgnoreFields(this, Set.of("file_id", "update_file_name", "col_value", "col_name"));
            }
            default -> throw new IllegalArgumentException(ErrCodeEnum.BIZ_TYPE_NOT_EXIST.getErrMsg());
        }
    }


    private String serializeWithIgnoreFields(PyLabelReq pyLabelReq, Set<String> ignoreFields) {
        ObjectMapper mapper = new ObjectMapper();

        FilterProvider filters = new SimpleFilterProvider()
                .addFilter("dynamicFilter", SimpleBeanPropertyFilter.serializeAllExcept(ignoreFields));
        try {
            return mapper.writer(filters).writeValueAsString(pyLabelReq);
        } catch (JsonProcessingException e) {
            log.error(e.getMessage(), e);
            throw new RuntimeException(e);
        }
    }
}
