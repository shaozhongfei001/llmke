package com.gientech.tools.database.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.tools.database.domain.convertor.TLTableFileConvertor;
import com.gientech.tools.database.domain.entity.TLTableFile;
import com.gientech.tools.database.domain.mapper.TLTableFileMapper;
import com.gientech.tools.database.domain.model.TLTableFileDO;
import com.gientech.tools.database.domain.repository.TLTableFileRepository;
import com.gientech.tools.database.infrastructure.enums.FileParseStatusEnum;
import org.springframework.stereotype.Repository;

import java.util.Date;
import java.util.List;
import java.util.Objects;

@Repository
public class TLTableFileRepositoryImpl extends ServiceImpl<TLTableFileMapper, TLTableFileDO> implements TLTableFileRepository {
    @Override
    public Boolean save(TLTableFile tlTableFile) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        tlTableFile.setGmtCreate(new Date());
        tlTableFile.setGmtModified(new Date());
        tlTableFile.setCreateBy(userName);
        tlTableFile.setUpdateBy(userName);
        TLTableFileDO tlTableFileDO = BeanUtil.copyProperties(tlTableFile, TLTableFileDO.class);
        boolean save = super.save(tlTableFileDO);
        tlTableFile.setId(tlTableFileDO.getId());
        return save;
    }

    @Override
    public List<TLTableFile> listByTableId(Long tableId) {
        LambdaQueryWrapper<TLTableFileDO> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(TLTableFileDO::getTableId, tableId)
                .orderByDesc(TLTableFileDO::getGmtCreate);
        List<TLTableFileDO> tlTableDOS = super.baseMapper.selectList(queryWrapper);
        return TLTableFileConvertor.INSTANCE.tlTableFileDOList2TLTableFileList(tlTableDOS);
    }

    @Override
    public List<TLTableFile> listUploadedByTableId(Long tableId) {
        LambdaQueryWrapper<TLTableFileDO> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(TLTableFileDO::getTableId, tableId).ne(TLTableFileDO::getStatus, FileParseStatusEnum.S10.getCode())
                .orderByDesc(TLTableFileDO::getGmtCreate);
        List<TLTableFileDO> tlTableDOS = super.baseMapper.selectList(queryWrapper);
        return TLTableFileConvertor.INSTANCE.tlTableFileDOList2TLTableFileList(tlTableDOS);
    }

    @Override
    public TLTableFile findById(Long id) {
        TLTableFileDO tlTableFileDO = super.baseMapper.selectById(id);
        return Objects.isNull(tlTableFileDO) ? null : BeanUtil.copyProperties(tlTableFileDO, TLTableFile.class);
    }

    @Override
    public TLTableFile findByTableIdAndDatabaseId(Long tableId, Long databaseId) {
        LambdaQueryWrapper<TLTableFileDO> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(TLTableFileDO::getTableId, tableId).eq(TLTableFileDO::getDatabaseId, databaseId);
        TLTableFileDO tlTableFileDO = baseMapper.selectOne(queryWrapper);
        return Objects.isNull(tlTableFileDO) ? null : BeanUtil.copyProperties(tlTableFileDO, TLTableFile.class);
    }

    @Override
    public List<TLTableFile> findByDatabaseId(Long databaseId) {
        LambdaQueryWrapper<TLTableFileDO> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(TLTableFileDO::getDatabaseId, databaseId)
                .orderByDesc(TLTableFileDO::getGmtCreate);
        List<TLTableFileDO> tlTableDOS = super.baseMapper.selectList(queryWrapper);
        return TLTableFileConvertor.INSTANCE.tlTableFileDOList2TLTableFileList(tlTableDOS);
    }

    @Override
    public List<TLTableFile> findImportedByDatabaseId(Long databaseId) {
        LambdaQueryWrapper<TLTableFileDO> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(TLTableFileDO::getDatabaseId, databaseId).ne(TLTableFileDO::getStatus, FileParseStatusEnum.S10.getCode())
                .orderByDesc(TLTableFileDO::getGmtCreate);
        List<TLTableFileDO> tlTableDOS = super.baseMapper.selectList(queryWrapper);
        return TLTableFileConvertor.INSTANCE.tlTableFileDOList2TLTableFileList(tlTableDOS);
    }

    @Override
    public Boolean updateById(TLTableFile tlTableFile) {
        Long id = tlTableFile.getId();
        if (null == id) throw new RuntimeException("主键参数必传");

        TLTableFile oldTLTableFile = findById(id);
        if (null == oldTLTableFile) throw new RuntimeException("主键参数查询出的对象为空");

        tlTableFile.setCreateBy(oldTLTableFile.getCreateBy());
        tlTableFile.setGmtCreate(oldTLTableFile.getGmtCreate());

        User user = UserContext.getUser();
        String userName = user.getUserName();
        tlTableFile.setGmtModified(new Date());
        tlTableFile.setUpdateBy(userName);

        TLTableFileDO tlTableFileDO = BeanUtil.copyProperties(tlTableFile, TLTableFileDO.class);

        return super.updateById(tlTableFileDO);
    }

    @Override
    public Integer deleteById(Long id) {
        return super.baseMapper.deleteById(id);
    }

    @Override
    public Integer deleteByIdAndStatus(Long fileId, String status) {
        LambdaQueryWrapper<TLTableFileDO> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(TLTableFileDO::getId, fileId)
                .eq(TLTableFileDO::getStatus, status);

        return super.baseMapper.delete(queryWrapper);
    }

    @Override
    public Integer deleteByTableId(Long tableId) {
        LambdaQueryWrapper<TLTableFileDO> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(TLTableFileDO::getTableId, tableId);

        return super.baseMapper.delete(queryWrapper);
    }

    @Override
    public Integer deleteNotImportFileByName(Long fileId, String originalFileName) {
        LambdaQueryWrapper<TLTableFileDO> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(TLTableFileDO::getOriginalFilename, originalFileName);
        queryWrapper.eq(TLTableFileDO::getStatus, FileParseStatusEnum.S10.getCode());
        queryWrapper.ne(TLTableFileDO::getId, fileId);
        return super.baseMapper.delete(queryWrapper);
    }

    @Override
    public Integer deleteByTableId(Long tableId, String status) {
        LambdaQueryWrapper<TLTableFileDO> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(TLTableFileDO::getTableId, tableId)
                .eq(TLTableFileDO::getStatus, status);
        return super.baseMapper.delete(queryWrapper);
    }
}
