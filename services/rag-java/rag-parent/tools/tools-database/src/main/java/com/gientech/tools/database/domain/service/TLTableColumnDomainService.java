package com.gientech.tools.database.domain.service;

import com.gientech.tools.database.domain.entity.TLTableColumn;

import java.util.List;

public interface TLTableColumnDomainService {
    Boolean save(TLTableColumn tlTableColumn);
    Boolean batchSave(List<TLTableColumn> tlTableColumns);
    List<TLTableColumn> listByTableId(Long tableId, Boolean isHaveDefField);
    TLTableColumn findById(Long id);
    Boolean updateById(TLTableColumn tlTableColumn);
    Integer deleteById(Long id);
}
