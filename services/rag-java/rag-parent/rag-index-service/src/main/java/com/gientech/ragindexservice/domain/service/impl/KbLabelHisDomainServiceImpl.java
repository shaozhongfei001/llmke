package com.gientech.ragindexservice.domain.service.impl;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragindexservice.domain.entity.KbLabelHis;
import com.gientech.ragindexservice.domain.repository.KbLabelHisRepository;
import com.gientech.ragindexservice.domain.service.KbLabelHisDomainService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class KbLabelHisDomainServiceImpl implements KbLabelHisDomainService {

    @Autowired
    private KbLabelHisRepository kbLabelHisRepository;

    @Override
    public KbLabelHis findById(Long id) {
        return kbLabelHisRepository.findById(id);
    }

    @Override
    public Boolean save(KbLabelHis kbLabelHis) {
        return kbLabelHisRepository.save(kbLabelHis);
    }

    @Override
    public Boolean updateById(KbLabelHis kbLabelHis) {
        return kbLabelHisRepository.updateById(kbLabelHis);
    }

    @Override
    public Page<KbLabelHis> list(Long pageNo, Long pageSize) {
        return kbLabelHisRepository.list(pageNo, pageSize);
    }

    @Override
    public void addLabelsHis(Long kbId, String label) {
//        KbLabelHis kbLabelHis = kbLabelHisRepository.findByKbId(kbId);
//        if(Objects.isNull(kbLabelHis))

    }
}
