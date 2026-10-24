package com.gientech.ragindexservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.plugins.pagination.PageDTO;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragindexservice.application.service.KbLabelHisAppService;
import com.gientech.ragindexservice.domain.entity.KbLabelHis;
import com.gientech.ragindexservice.domain.entity.KnowledgeBase;
import com.gientech.ragindexservice.domain.service.KbLabelHisDomainService;
import com.gientech.ragcommon.index.dto.KbLabelHisDTO;
import com.gientech.ragcommon.index.request.SaveKbLabelHisReq;
import com.gientech.ragcommon.index.request.UpdateKbLabelHisReq;
import com.gientech.ragindexservice.domain.service.KnowledgeBaseDomainService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import java.util.Objects;

@Service
public class KbLabelHisAppServiceImpl implements KbLabelHisAppService {

    @Autowired
    private KbLabelHisDomainService kbLabelHisDomainService;
    
    @Autowired
    private KnowledgeBaseDomainService knowledgeBaseDomainService;

    @Override
    public KbLabelHisDTO findById(Long id) {
        if(Objects.isNull(id))
            return null;
        KbLabelHis byId = kbLabelHisDomainService.findById(id);
        return BeanUtil.copyProperties(byId,KbLabelHisDTO.class);
    }

    @Override
    public Boolean save(SaveKbLabelHisReq kbLabelHisReq) {
        if(Objects.isNull(kbLabelHisReq))
            return false;
       return kbLabelHisDomainService.save(BeanUtil.copyProperties(kbLabelHisReq,KbLabelHis.class));
    }

    @Override
    public Boolean updateById(UpdateKbLabelHisReq kbLabelHisReq) {
        if(Objects.isNull(kbLabelHisReq))
            return false;
        return kbLabelHisDomainService.updateById(BeanUtil.copyProperties(kbLabelHisReq,KbLabelHis.class));
    }

    @Override
    public Page<KbLabelHisDTO> list(Long pageNo, Long pageSize) {
        pageNo = Objects.isNull(pageNo) ? 1 : pageNo;
        pageSize = Objects.isNull(pageSize) ? 10 : pageSize;
        Page<KbLabelHis> page = kbLabelHisDomainService.list(pageNo, pageSize);
        Page<KbLabelHisDTO> result = new PageDTO<>();
        BeanUtil.copyProperties(page,result);
        result.setRecords(BeanUtil.copyToList(page.getRecords(),KbLabelHisDTO.class));
        return result;
    }
}
