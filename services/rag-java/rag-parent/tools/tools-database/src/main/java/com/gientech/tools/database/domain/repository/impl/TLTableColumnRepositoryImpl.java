package com.gientech.tools.database.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.tools.database.domain.convertor.TLTableColumnConvertor;
import com.gientech.tools.database.domain.entity.TLTableColumn;
import com.gientech.tools.database.domain.mapper.TLTableColumnMapper;
import com.gientech.tools.database.domain.model.TLTableColumnDO;
import com.gientech.tools.database.domain.repository.TLTableColumnRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;

import java.util.Date;
import java.util.List;
import java.util.Objects;

@Repository
public class TLTableColumnRepositoryImpl extends ServiceImpl<TLTableColumnMapper, TLTableColumnDO> implements TLTableColumnRepository {
    @Autowired
    private TLTableColumnMapper tlTableColumnMapper;

    @Override
    public Boolean save(TLTableColumn tlTableColumn) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        tlTableColumn.setGmtCreate(new Date());
        tlTableColumn.setGmtModified(new Date());
        tlTableColumn.setCreateBy(userName);
        tlTableColumn.setUpdateBy(userName);
        TLTableColumnDO tlTableColumnDO = BeanUtil.copyProperties(tlTableColumn, TLTableColumnDO.class);
        boolean save = super.save(tlTableColumnDO);
        tlTableColumn.setId(tlTableColumnDO.getId());
        return save;
    }

    @Override
    public Boolean batchSave(List<TLTableColumn> tlTableColumns) {
        if(tlTableColumns==null||tlTableColumns.size()==0) {
            return true;
        }
        User user = UserContext.getUser();
        String userName = user.getUserName();

        for(TLTableColumn tlTableColumn:tlTableColumns) {
            tlTableColumn.setGmtCreate(new Date());
            tlTableColumn.setGmtModified(new Date());
            tlTableColumn.setCreateBy(userName);
            tlTableColumn.setUpdateBy(userName);
        }
        List<TLTableColumnDO> tlTableColumnDOS = TLTableColumnConvertor.INSTANCE.tlTableColumnList2TLTableColumnDOList(tlTableColumns);
        tlTableColumnMapper.batchInsert(tlTableColumnDOS);
        return true;
    }

    @Override
    public List<TLTableColumn> listByTableId(Long tableId, Boolean isHaveDefField) {
        LambdaQueryWrapper<TLTableColumnDO> queryWrapper = new LambdaQueryWrapper<>();
        if(isHaveDefField){
            queryWrapper.eq(TLTableColumnDO::getTableId, tableId)
                    .orderByAsc(TLTableColumnDO::getId);
        } else {
            queryWrapper.eq(TLTableColumnDO::getTableId, tableId).ne(TLTableColumnDO::getPhysicalName, "file_id")
                    .orderByAsc(TLTableColumnDO::getId);
        }

        List<TLTableColumnDO> tlTableDOS = super.baseMapper.selectList(queryWrapper);
        List<TLTableColumn> tableList = TLTableColumnConvertor.INSTANCE.tlTableColumnDOList2TLTableColumnList(tlTableDOS);
        return tableList;
    }

    @Override
    public TLTableColumn findById(Long id) {
        TLTableColumnDO tlTableColumnDO = super.baseMapper.selectById(id);
        return Objects.isNull(tlTableColumnDO) ? null : BeanUtil.copyProperties(tlTableColumnDO, TLTableColumn.class);
    }

    @Override
    public Boolean updateById(TLTableColumn tlTableColumn) {
        Long id = tlTableColumn.getId();
        if(null == id) throw new RuntimeException("主键参数必传");

        TLTableColumn oldTLTableColumn = findById(id);
        if(null == oldTLTableColumn) throw new RuntimeException("主键参数查询出的对象为空");

        tlTableColumn.setCreateBy(oldTLTableColumn.getCreateBy());
        tlTableColumn.setGmtCreate(oldTLTableColumn.getGmtCreate());

        User user = UserContext.getUser();
        String userName = user.getUserName();
        tlTableColumn.setGmtModified(new Date());
        tlTableColumn.setUpdateBy(userName);

        TLTableColumnDO tlTableColumnDO = BeanUtil.copyProperties(tlTableColumn, TLTableColumnDO.class);

        return super.updateById(tlTableColumnDO);
    }

    @Override
    public Integer deleteById(Long id) {
        return super.baseMapper.deleteById(id);
    }

}
