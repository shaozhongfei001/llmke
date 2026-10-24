package com.gientech.ragindexservice.application.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.dto.KbLabelHisDTO;
import com.gientech.ragcommon.index.request.SaveKbLabelHisReq;
import com.gientech.ragcommon.index.request.UpdateKbLabelHisReq;

public interface KbLabelHisAppService {

    KbLabelHisDTO findById(Long id);

    Boolean save(SaveKbLabelHisReq kbLabelHisReq);

    Boolean updateById(UpdateKbLabelHisReq kbLabelHisReq);

    Page<KbLabelHisDTO> list(Long pageNo, Long pageSize);

}
