package com.gientech.ragindexservice.domain.service;

import com.alibaba.fastjson2.JSONObject;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.request.FaqQueryReq;
import com.gientech.ragindexservice.domain.entity.FaqEsInfo;
import com.gientech.ragindexservice.domain.entity.FaqInfo;
import com.gientech.ragcommon.index.request.FaqUpdateReq;

import java.util.List;

public interface ChunnkDomainService {

    /**
     * 通过id查询
     * @param primitiveName
     * @param pks
     * @return
     */
    List<JSONObject> getByChunkId(String primitiveName, List<Long> pks);

    /**
     * 列表查询
     * @param faqQueryReq
     * @return
     */
    Page<FaqInfo> pageList(FaqQueryReq faqQueryReq);

    Page<FaqInfo> pageFaqList(FaqQueryReq faqQueryReq);

    Page<FaqInfo> pageListFromLocal(FaqQueryReq faqQueryReq);

    /**
     * 列表查询(无分页)
     * @param faqQueryReq
     * @return
     */
    List<FaqInfo> faqList(FaqQueryReq faqQueryReq);

    /**
     * 删除表以及数据
     * @param tableName
     */
    void deleteTable(String tableName);

    /**
     * 删除文件
     * @param tableName
     * @param filePaths
     */
    void delFiles(String tableName, List<String> filePaths);

    /**
     * 删除FAQ数据
     * @param primitiveName
     * @param fileIds
     */
    void deleteFaq(String primitiveName, List<Long> fileIds, List<Long> faqFileIds);

    List<FaqEsInfo.FaqEsMetadata> findFaqsByFolderIds(String indexName, String folderIds);

    FaqEsInfo.FaqEsMetadata findFaqByPk(String indexName, Long pk);

    /**
     * 通过pk删除问答对
     * @param primitiveName
     * @param pks
     */
    void  deleteFaqByPks(String primitiveName,List<Long> pks);

    /**
     * 更新chunk中的字段(不能修改文本块的page_content、question、answer字段)
     * @param tableName
     * @param pks
     * @param colName
     * @param colValue
     */
    void updateChunkField(String tableName,List<Long> pks,String colName ,Object colValue);

    /**
     * 查询文本块
     * @param primitiveName
     * @param fileName
     * @param pageNo
     * @param pageSize
     * @return
     */
    JSONObject getChunks(String primitiveName, String fileName, Integer pageNo, Integer pageSize );

    /**
     * 批量更新FAQ
      * @param primitiveName
     * @param faqUpdateReqs
     */
    void updateFaqBatch(String primitiveName, List<FaqUpdateReq> faqUpdateReqs);


    void transferFaqBatch(String indexName, List<String> targetIds, Long targetFolderId);
}
