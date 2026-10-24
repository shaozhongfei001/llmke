package com.gientech.ragindexservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.index.enmus.IsDelEnums;
import com.gientech.ragindexservice.domain.entity.KbLabelHis;
import com.gientech.ragindexservice.domain.mapper.KbLabelHisMapper;
import com.gientech.ragindexservice.domain.model.KbLabelHisDO;
import com.gientech.ragindexservice.domain.repository.KbLabelHisRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import java.util.Date;
import java.util.List;
import java.util.Objects;

@Repository
public class  KbLabelHisRepositoryImpl implements  KbLabelHisRepository {

    @Autowired
    private  KbLabelHisMapper  kbLabelHisMapper;

    @Override
    public KbLabelHis findById(Long id) {
        KbLabelHisDO kbLabelHisDO = kbLabelHisMapper.selectById(id);
        return Objects.isNull(kbLabelHisDO) ? null : BeanUtil.copyProperties(kbLabelHisDO,KbLabelHis.class);
    }

    @Override
    public Boolean save(KbLabelHis kbLabelHis) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        kbLabelHis.setModifyBy(userName);
        kbLabelHis.setCreateBy(userName);
        kbLabelHis.setGmtCreate(new Date());
        kbLabelHis.setGmtModified(kbLabelHis.getGmtCreate());
        return kbLabelHisMapper.insert(BeanUtil.copyProperties(kbLabelHis, KbLabelHisDO.class)) > 0;
    }

    @Override
    public Boolean updateById(KbLabelHis kbLabelHis) {
        if (Objects.isNull(kbLabelHis.getId()))
            return false;
        User user = UserContext.getUser();
        String userName = user.getUserName();
        kbLabelHis.setModifyBy(userName);
        kbLabelHis.setGmtModified(new Date());
        return kbLabelHisMapper.updateById(BeanUtil.copyProperties(kbLabelHis, KbLabelHisDO.class)) > 0;
    }

    @Override
    public Page<KbLabelHis> list(Long pageNo, Long pageSize) {
        QueryWrapper<KbLabelHisDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.orderByDesc("gmt_create");
        Page<KbLabelHisDO> page = new Page<>(pageNo, pageSize);
        Page<KbLabelHisDO> pageResult = kbLabelHisMapper.selectPage(page, queryWrapper);
        Page<KbLabelHis> listPage = new Page<>();
        BeanUtil.copyProperties(pageResult,listPage);
        listPage.setRecords(BeanUtil.copyToList(pageResult.getRecords(),KbLabelHis.class));
        return listPage;
    }

    @Override
    public KbLabelHis findByKbId(Long kbId) {
        QueryWrapper<KbLabelHisDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("kb_id",kbId)
                .ne("is_del", IsDelEnums.DELETE.getCode())
                .last("limit 1");
        KbLabelHisDO kbLabelHisDO = kbLabelHisMapper.selectOne(queryWrapper);
        return Objects.isNull(kbLabelHisDO) ? null : BeanUtil.copyProperties(kbLabelHisDO,KbLabelHis.class);
    }
}
