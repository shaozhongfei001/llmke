package com.gientech.tools.database.domain.service.impl;

import com.gientech.tools.database.domain.entity.TLTableColumn;
import com.gientech.tools.database.domain.repository.TLTableColumnRepository;
import com.gientech.tools.database.domain.service.TLTableColumnDomainService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class TLTableColumnDomainServiceImpl implements TLTableColumnDomainService {
    private static final Logger log = LoggerFactory.getLogger(TLTableDomainServiceImpl.class);

    @Autowired
    private TLTableColumnRepository tlTableColumnRepository;

    @Override
    public Boolean save(TLTableColumn tlTableColumn) {
        return tlTableColumnRepository.save(tlTableColumn);
    }

    @Override
    public Boolean batchSave(List<TLTableColumn> tlTableColumns) {
        return tlTableColumnRepository.batchSave(tlTableColumns);
    }

    @Override
    public List<TLTableColumn> listByTableId(Long tableId, Boolean isHaveDefField) {
        return tlTableColumnRepository.listByTableId(tableId, isHaveDefField);
    }

    @Override
    public TLTableColumn findById(Long id) {
        return tlTableColumnRepository.findById(id);
    }

    @Override
    public Boolean updateById(TLTableColumn tlTableColumn) {
        return tlTableColumnRepository.updateById(tlTableColumn);
    }

    @Override
    public Integer deleteById(Long id) {
        return tlTableColumnRepository.deleteById(id);
    }
}
