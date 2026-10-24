package com.gientech.elasticsearchservice.application.request;

import com.gientech.elasticsearchservice.document.FullTextDoc;
import com.gientech.elasticsearchservice.document.MetaData;
import com.gientech.elasticsearchservice.infrastructure.util.DateTimeUtil;
import lombok.Data;
import org.springframework.util.CollectionUtils;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/9/23 13:46
 */
@Data
public class DocUpdateRequest<T extends FullTextDoc> {
    private String indexName;
    private List<T> docList;

    public List<String> getDocPkList() {
        if (CollectionUtils.isEmpty(docList)) {
            return new ArrayList<>();
        }
        return docList.stream().map(doc -> doc.getMetaData().getPk()).collect(Collectors.toList());
    }

    public void updateDocTime() {
        if (!CollectionUtils.isEmpty(docList)) {
            docList.stream().forEach(doc -> doc.getMetaData().setUpdateTime(DateTimeUtil.getFormattedNow()));
        }
    }

}
