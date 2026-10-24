package com.gientech.elasticsearchservice.application.request;

import co.elastic.clients.elasticsearch._types.FieldValue;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.util.CollectionUtils;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/9/20 17:43
 */
@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class DocDeleteRequest {
    private String indexName;
    private String colName;
    private List<String> colValues;

    public List<FieldValue> getColValuesFieldValue() {
        if (CollectionUtils.isEmpty(colValues)) {
            return new ArrayList<>();
        }
        return colValues.stream()
                .map(FieldValue::of)
                .collect(Collectors.toList());
    }
}
