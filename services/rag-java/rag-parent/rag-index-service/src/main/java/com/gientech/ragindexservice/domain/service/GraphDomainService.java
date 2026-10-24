package com.gientech.ragindexservice.domain.service;

import org.jodconverter.local.office.utils.Lo;

import java.util.List;

public interface GraphDomainService {

    /**
     * 删除图
     * @param spaceName
     * @param fileId
     * @return
     */
    Boolean delGraphSpace(String spaceName, Long fileId);

    /**
     * 删除图milvus中的entity数据
     * @param spaceName
     * @param fileIds
     * @param fileNames
     * @return
     */
    Boolean delGraphEntity(String spaceName,List<String> fileIds,List<String> fileNames);
}
