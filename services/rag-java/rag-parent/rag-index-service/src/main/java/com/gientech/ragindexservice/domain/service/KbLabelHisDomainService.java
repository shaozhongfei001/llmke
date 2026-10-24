package com.gientech.ragindexservice.domain.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragindexservice.domain.entity.KbLabelHis;

public interface KbLabelHisDomainService {

    KbLabelHis findById(Long id);

    Boolean save(KbLabelHis kbLabelHis);

    Boolean updateById(KbLabelHis kbLabelHis);

    Page<KbLabelHis> list(Long pageNo, Long pageSize);

    void addLabelsHis(Long kbId, String label);
}
