package com.gientech.ragindexservice.application.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.dto.SynLogDTO;

public interface SynLogAppService {

    Page<SynLogDTO> list(Long pageNo, Long pageSize, Long fileId);
}
