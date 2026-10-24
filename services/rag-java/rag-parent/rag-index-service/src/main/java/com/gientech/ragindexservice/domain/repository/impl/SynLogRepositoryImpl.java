package com.gientech.ragindexservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragindexservice.domain.entity.SynLog;
import com.gientech.ragindexservice.domain.mapper.SynLogMapper;
import com.gientech.ragindexservice.domain.model.SynLogDO;
import com.gientech.ragindexservice.domain.repository.SynLogRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;

import java.util.*;

@Repository
public class SynLogRepositoryImpl implements SynLogRepository {

    @Autowired
    private SynLogMapper synLogMapper;

    @Override
    public SynLog findById(Long kbId, Long fileId) {
        QueryWrapper<SynLogDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("kb_id", kbId)
                .eq("target_id", fileId)
                .last("limit 1");
        SynLogDO synLogDO = synLogMapper.selectOne(queryWrapper);
        return Objects.isNull(synLogDO) ? null : BeanUtil.copyProperties(synLogDO, SynLog.class);
    }

    @Override
    public void save(SynLog synLog) {
        User user = UserContext.getUser();
        if(!Objects.isNull(user)){
            String userName = user.getUserName();
            synLog.setUpdateBy(userName);
            synLog.setCreateBy(userName);
        }
        synLog.setGmtCreate(new Date());
        synLog.setGmtModified(synLog.getGmtCreate());
        synLogMapper.insert(BeanUtil.copyProperties(synLog, SynLogDO.class));
    }

    @Override
    public void updateById(SynLog synLog) {
        if (Objects.isNull(synLog.getId()))
            return;
        User user = UserContext.getUser();
        if(!Objects.isNull(user)){
            String userName = user.getUserName();
            synLog.setUpdateBy(userName);
        }
        synLog.setGmtModified(new Date());
        synLogMapper.updateById(BeanUtil.copyProperties(synLog, SynLogDO.class));
    }

    @Override
    public List<SynLog> findByFileIds(List<Long> fileIds) {
        QueryWrapper<SynLogDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.in("target_id",fileIds);
        List<SynLogDO> synLogDOS = synLogMapper.selectList(queryWrapper);
        return Objects.isNull(synLogDOS) ? null : BeanUtil.copyToList(synLogDOS,SynLog.class);
    }

    @Override
    public Page<SynLog> page(Long pageNo, Long pageSize, Long fileId) {
        LambdaQueryWrapper<SynLogDO> wrapper = Wrappers.lambdaQuery(SynLogDO.class)
                .eq(SynLogDO::getTargetId,fileId)
                .orderByDesc(SynLogDO::getGmtCreate);
        Page<SynLogDO> page = new Page<>(pageNo, pageSize);
        Page<SynLogDO> pageResult = synLogMapper.selectPage(page, wrapper);
        Page<SynLog> result = new Page<>();
        BeanUtil.copyProperties(pageResult, result);
        result.setRecords(BeanUtil.copyToList(pageResult.getRecords(), SynLog.class));
        return result;
    }

    @Override
    public SynLog findByFileId(Long fileId) {
        LambdaQueryWrapper<SynLogDO> wrapper = Wrappers.lambdaQuery(SynLogDO.class)
                .eq(SynLogDO::getTargetId,fileId)
                .orderByDesc(SynLogDO::getGmtCreate).last("limit 1");
        SynLogDO synLogDO = synLogMapper.selectOne(wrapper);
        return Objects.isNull(synLogDO) ? null : BeanUtil.copyProperties(synLogDO,SynLog.class);
    }
}
