package com.gientech.elasticsearchservice.application.request;

import co.elastic.clients.elasticsearch._types.FieldValue;
import lombok.Data;
import org.springframework.util.CollectionUtils;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/9/20 17:28
 */
@Data
public class DocQueryRequest {
    private String indexName;
    private List<String> documentIds;


    public List<FieldValue> getDocIdsFieldValue() {
        if (CollectionUtils.isEmpty(documentIds)) {
            return new ArrayList<>();
        }
        return documentIds.stream()
                .map(FieldValue::of)
                .collect(Collectors.toList());
    }
}
