package com.gientech.ragindexservice.domain.repository;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragindexservice.domain.entity.SynLog;

import java.util.List;

public interface SynLogRepository {

    SynLog findById(Long kbId, Long fileId);

    void save(SynLog synLog);

    void updateById(SynLog synLog);

    List<SynLog> findByFileIds(List<Long> fileIds);

    Page<SynLog> page(Long pageNo, Long pageSize, Long fileId);

    SynLog findByFileId(Long fileId);
}
