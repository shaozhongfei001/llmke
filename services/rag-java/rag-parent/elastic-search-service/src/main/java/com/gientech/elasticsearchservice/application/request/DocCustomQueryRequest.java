package com.gientech.elasticsearchservice.application.request;

import co.elastic.clients.elasticsearch._types.FieldValue;
import co.elastic.clients.elasticsearch._types.SortOrder;
import lombok.Data;
import org.springframework.util.CollectionUtils;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/9/23 11:17
 */
@Data
public class DocCustomQueryRequest {
    private List<String> indexName;
    private String colName;
    private List<String> colValues;
    private String sortField = "update_time";
    private SortOrder sortMode = SortOrder.Desc;
    private int pageNo = 1;
    private int pageNum = 500;

    public List<FieldValue> getColValuesFieldValue() {
        if (CollectionUtils.isEmpty(colValues)) {
            return new ArrayList<>();
        }
        return colValues.stream()
                .map(FieldValue::of)
                .collect(Collectors.toList());
    }
}
