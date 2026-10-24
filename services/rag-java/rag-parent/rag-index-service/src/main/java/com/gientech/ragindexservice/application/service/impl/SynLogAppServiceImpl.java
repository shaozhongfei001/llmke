package com.gientech.ragindexservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.dto.SynLogDTO;
import com.gientech.ragindexservice.application.service.SynLogAppService;
import com.gientech.ragindexservice.domain.entity.SynLog;
import com.gientech.ragindexservice.domain.service.SynLogDomainService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.ZoneId;
import java.time.format.DateTimeFormatter;

import static cn.hutool.core.date.DateUtil.formatDate;


@Service
public class SynLogAppServiceImpl implements SynLogAppService {

    @Autowired
    private SynLogDomainService synLogDomainService;

    @Override
    public Page<SynLogDTO> list(Long pageNo, Long pageSize, Long fileId) {
        Page<SynLog> synLogPage = synLogDomainService.page(pageNo,pageSize,fileId);
        Page<SynLogDTO> result = new Page<>();
        BeanUtil.copyProperties(synLogPage, result);
        result.setRecords(BeanUtil.copyToList(synLogPage.getRecords(), SynLogDTO.class));
        return result;
    }
}
