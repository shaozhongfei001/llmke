package com.gientech.ragindexservice.application.service;

import cn.hutool.db.Entity;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.dto.tools.TLDatabaseDTO;
import com.gientech.ragcommon.index.request.QueryDataReq;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;
import java.util.Set;

public interface TLDatabaseAppService {

    /**
     * 数据库配置分页查询
     *
     * @param pageNo
     * @param pageSize
     * @param fuzzyWord 模糊搜索关键字
     * @return
     */
    Page<TLDatabaseDTO> pageDBList(Long pageNo, Long pageSize, String fuzzyWord, String userName, Boolean includingCreator);

    /**
     * 查询共享数据库列表
     *
     * @param pageNo
     * @param pageSize
     * @param fuzzyWord
     * @return
     */
    Page<TLDatabaseDTO> shareDBList(Long pageNo, Long pageSize, String fuzzyWord);

    Set<TLDatabaseDTO> searchAllDB(String fuzzyWord);

    /**
     * 查询数据库的创建者
     *
     * @param databaseId
     * @return
     */
    String queryDatabaseCreator(Long databaseId);

    /**
     * 执行sql查询数据
     *
     * @param executeSqlReq
     * @return
     */
    List<Entity> queryData(QueryDataReq executeSqlReq);

    /**
     * 上传Excel、Csv数据表
     * 上传单个文件
     *
     * @param multipartFile
     * @return
     */
    Long uploadFile(Long databaseId, Long tableId, MultipartFile multipartFile);

    /**
     * 取消上传文件
     *
     * @param fileIds
     * @return
     */
    Boolean cancelUploadFile(List<Long> fileIds);

    /**
     * 传入多个文件id，解析文件
     *
     * @param fileIds
     * @param tableDescriptionMap 自定义表描述
     * @param isGenDescription
     */
    void parseFiles(List<Long> fileIds, Map<Long, String> tableDescriptionMap, Boolean isGenDescription);

    /**
     * 解析追加数据文件
     *
     * @param fileIds
     * @param tableId
     */
    void parseAppendFiles(List<Long> fileIds, Long tableId);

    /**
     * 重新解析上传文件
     *
     * @param fileId
     */
    void reParseFile(Long fileId);

    TLDatabaseDTO findById(Long databaseId);
}
