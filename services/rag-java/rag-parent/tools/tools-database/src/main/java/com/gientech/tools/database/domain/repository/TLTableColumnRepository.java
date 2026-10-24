package com.gientech.tools.database.domain.repository;

import com.baomidou.mybatisplus.extension.service.IService;
import com.gientech.tools.database.domain.entity.TLTableColumn;
import com.gientech.tools.database.domain.model.TLTableColumnDO;

import java.util.List;

public interface TLTableColumnRepository extends IService<TLTableColumnDO> {
    Boolean save(TLTableColumn tlTableColumn);
    Boolean batchSave(List<TLTableColumn> tlTableColumns);
    List<TLTableColumn> listByTableId(Long tableId, Boolean isHaveDefField);
    TLTableColumn findById(Long id);
    Boolean updateById(TLTableColumn tlTableColumn);
    Integer deleteById(Long id);
}
