package com.gientech.ragindexservice.domain.repository;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragindexservice.domain.entity.KbLabelHis;

public interface KbLabelHisRepository {

   KbLabelHis findById(Long id);

    Boolean save(KbLabelHis kbLabelHis);

    Boolean updateById(KbLabelHis kbLabelHis);

    Page<KbLabelHis> list(Long pageNo, Long pageSize);

    KbLabelHis findByKbId(Long kbId);
}
