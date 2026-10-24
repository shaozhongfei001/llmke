package com.gientech.tools.database.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.date.DateUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.tools.database.domain.convertor.TLTableConvertor;
import com.gientech.tools.database.domain.entity.TLTable;
import com.gientech.tools.database.domain.mapper.TLTableMapper;
import com.gientech.tools.database.domain.model.TLTableDO;
import com.gientech.tools.database.domain.repository.TLTableRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Objects;

@Repository
public class TLTableRepositoryImpl extends ServiceImpl<TLTableMapper, TLTableDO> implements TLTableRepository {

    @Autowired
    private TLTableMapper tlTableMapper;

    @Override
    public Boolean save(TLTable tlTable) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        tlTable.setGmtCreate(new Date());
        tlTable.setGmtModified(new Date());
        tlTable.setCreateBy(userName);
        tlTable.setUpdateBy(userName);
        TLTableDO tlTableDO = BeanUtil.copyProperties(tlTable, TLTableDO.class);
        boolean save = super.save(tlTableDO);
        tlTable.setId(tlTableDO.getId());
        return save;
    }

    @Override
    public Page<TLTable> page(Long databaseId, Long pageNo, Long pageSize) {
        LambdaQueryWrapper<TLTableDO> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(TLTableDO::getDatabaseId, databaseId)
                .orderByDesc(TLTableDO::getGmtCreate);
        Page<TLTableDO> page = new Page<>(pageNo, pageSize);
        Page<TLTable> listPage = tlTableMapper.queryPage(page, queryWrapper);
        return listPage;
    }

    @Override
    public List<TLTable> list(Long databaseId) {
        LambdaQueryWrapper<TLTableDO> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(TLTableDO::getDatabaseId, databaseId)
                .orderByDesc(TLTableDO::getGmtCreate);
        List<TLTableDO> tlTableDOS = super.baseMapper.selectList(queryWrapper);
        List<TLTable> tableList = TLTableConvertor.INSTANCE.tlTableDOList2TLTableList(tlTableDOS);
        return tableList;
    }

    @Override
    public TLTable findById(Long id) {
        TLTableDO tlTableDO = super.baseMapper.selectById(id);
        return Objects.isNull(tlTableDO) ? null : BeanUtil.copyProperties(tlTableDO, TLTable.class);
    }

    @Override
    public TLTable findByTableName(Long databaseId, String tableName) {
        LambdaQueryWrapper<TLTableDO> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(TLTableDO::getDatabaseId, databaseId)
                .eq(TLTableDO::getPhysicalName, tableName);
        TLTableDO tlTableDO = super.baseMapper.selectOne(queryWrapper);
        return Objects.isNull(tlTableDO) ? null : BeanUtil.copyProperties(tlTableDO, TLTable.class);
    }

    @Override
    public TLTable findByBusinessName(Long databaseId, String businessName) {
        LambdaQueryWrapper<TLTableDO> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(TLTableDO::getDatabaseId, databaseId)
                .eq(TLTableDO::getBusinessName, businessName);
        TLTableDO tlTableDO = super.baseMapper.selectOne(queryWrapper);
        return Objects.isNull(tlTableDO) ? null : BeanUtil.copyProperties(tlTableDO, TLTable.class);
    }


    @Override
    public Boolean updateById(TLTable tlTable) {
        Long id = tlTable.getId();
        if(null == id) throw new RuntimeException("主键参数必传");

        TLTable oldTLTable = findById(id);
        if(null == oldTLTable) throw new RuntimeException("主键参数查询出的对象为空");

        tlTable.setCreateBy(oldTLTable.getCreateBy());
        tlTable.setGmtCreate(oldTLTable.getGmtCreate());

        User user = UserContext.getUser();
        String userName = user.getUserName();
        tlTable.setGmtModified(new Date());
        tlTable.setUpdateBy(userName);

        TLTableDO tlTableDO = BeanUtil.copyProperties(tlTable, TLTableDO.class);

        return super.updateById(tlTableDO);
    }

    @Override
    public Long countTables(Long databaseId) {
        LambdaQueryWrapper<TLTableDO> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(TLTableDO::getDatabaseId, databaseId);
        Long count = super.baseMapper.selectCount(queryWrapper);
        return count;
    }

    @Override
    public Integer deleteById(Long id) {
        return super.baseMapper.deleteById(id);
    }

    @Override
    public Integer deleteByDatabaseId(Long databaseId) {
        LambdaQueryWrapper<TLTableDO> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(TLTableDO::getDatabaseId, databaseId)
                .orderByDesc(TLTableDO::getGmtCreate);
        int delete = super.baseMapper.delete(queryWrapper);

        return delete;
    }
}
