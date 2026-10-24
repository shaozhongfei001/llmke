package com.gientech.ragindexservice.domain.service;

import com.alibaba.fastjson2.JSONObject;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragindexservice.domain.entity.SynLog;
import java.util.List;
/**
 * <p>
 * 日志 服务实现类
 * </p>
 *
 * @author wudf
 * @since 2024-08-27
 */
public interface SynLogDomainService {

    SynLog findById(Long kbId, Long fileId);

    void saveOrUpdate(SynLog synLog);

    List<SynLog> findByFileIds(List<Long> fileIds);

    void saveLog(Long kbId, Long fileId, Integer logType, JSONObject respObj,String errorMsg);

    void saveLog(Long kbId, Long fileId, Integer logType, JSONObject respObj,String errorMsg,String errorDetail);

    Page<SynLog> page(Long pageNo, Long pageSize, Long fileId);

    SynLog findByFileId(Long id);
}
