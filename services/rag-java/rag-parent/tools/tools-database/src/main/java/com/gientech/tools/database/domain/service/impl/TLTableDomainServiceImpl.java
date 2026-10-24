package com.gientech.tools.database.domain.service.impl;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.tools.database.domain.entity.TLTable;
import com.gientech.tools.database.domain.repository.TLTableRepository;
import com.gientech.tools.database.domain.service.TLTableDomainService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class TLTableDomainServiceImpl implements TLTableDomainService {
    private static final Logger log = LoggerFactory.getLogger(TLTableDomainServiceImpl.class);

    @Autowired
    private TLTableRepository tlTableRepository;

    @Override
    public Boolean save(TLTable tlTable) {
        Boolean save = tlTableRepository.save(tlTable);
        return save;
    }

    @Override
    public Page<TLTable> page(Long databaseId, Long pageNo, Long pageSize) {
        return tlTableRepository.page(databaseId, pageNo, pageSize);
    }

    @Override
    public List<TLTable> list(Long databaseId) {
        return tlTableRepository.list(databaseId);
    }

    @Override
    public TLTable findById(Long id) {
        return tlTableRepository.findById(id);
    }

    @Override
    public TLTable findByTableName(Long databaseId, String tableName) {
        return tlTableRepository.findByTableName(databaseId, tableName);
    }

    @Override
    public TLTable findByBusinessName(Long databaseId, String businessName) {
        return tlTableRepository.findByBusinessName(databaseId, businessName);
    }

    @Override
    public Boolean updateById(TLTable tlTable) {
        Boolean save = tlTableRepository.updateById(tlTable);
        return save;
    }

    @Override
    public Long countTables(Long databaseId) {
        return tlTableRepository.countTables(databaseId);
    }

    @Override
    public Integer deleteById(Long id) {
        return tlTableRepository.deleteById(id);
    }

    @Override
    public Integer deleteByDatabaseId(Long databaseId) {
        return tlTableRepository.deleteByDatabaseId(databaseId);
    }
}
