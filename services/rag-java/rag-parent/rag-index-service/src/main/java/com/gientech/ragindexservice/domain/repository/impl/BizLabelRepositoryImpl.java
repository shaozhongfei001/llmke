package com.gientech.ragindexservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.DomainException;
import com.gientech.ragindexservice.domain.entity.BizLabel;
import com.gientech.ragindexservice.domain.mapper.BizLabelMapper;
import com.gientech.ragindexservice.domain.model.BizLabelDO;
import com.gientech.ragindexservice.domain.repository.BizLabelRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import org.springframework.util.CollectionUtils;

import java.util.Date;
import java.util.List;
import java.util.Objects;

@Repository
public class BizLabelRepositoryImpl extends ServiceImpl<BizLabelMapper, BizLabelDO> implements BizLabelRepository {

    @Autowired
    private BizLabelMapper bizLabelMapper;

    @Override
    public BizLabel findById(Long id) {
        BizLabelDO bizLabelDO = bizLabelMapper.selectById(id);
        return Objects.isNull(bizLabelDO) ? null : BeanUtil.copyProperties(bizLabelDO, BizLabel.class);
    }

    @Override
    public Boolean save(BizLabel bizLabel) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        bizLabel.setUpdateBy(userName);
        bizLabel.setCreateBy(userName);
        LambdaQueryWrapper<BizLabelDO> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.eq(BizLabelDO::getBizType, bizLabel.getBizType())
                .eq(BizLabelDO::getTargetId, bizLabel.getTargetId())
                .eq(BizLabelDO::getLabel, bizLabel.getLabel());
        if (Objects.nonNull(bizLabelMapper.selectOne(queryWrapper))) {
            throw new DomainException(ErrCodeEnum.LABEL_EXISTS);
        }
        return bizLabelMapper.insert(BeanUtil.copyProperties(bizLabel, BizLabelDO.class)) > 0;
    }

    @Override
    public Boolean updateById(BizLabel bizLabel) {
        if (Objects.isNull(bizLabel.getId()))
            return false;
        User user = UserContext.getUser();
        String userName = user.getUserName();
        bizLabel.setUpdateBy(userName);
        bizLabel.setGmtModified(new Date());
        return bizLabelMapper.updateById(BeanUtil.copyProperties(bizLabel, BizLabelDO.class)) > 0;
    }

    @Override
    public Page<BizLabel> list(Long pageNo, Long pageSize) {
        QueryWrapper<BizLabelDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.orderByDesc("gmt_create");
        Page<BizLabelDO> page = new Page<>(pageNo, pageSize);
        Page<BizLabelDO> pageResult = bizLabelMapper.selectPage(page, queryWrapper);
        Page<BizLabel> listPage = new Page<>();
        BeanUtil.copyProperties(pageResult, listPage);
        listPage.setRecords(BeanUtil.copyToList(pageResult.getRecords(), BizLabel.class));
        return listPage;
    }

    @Override
    public Boolean deleteById(Long id) {
        return bizLabelMapper.deleteById(id) > 0;
    }

    @Override
    public int deleteBatch(BizLabel bizLabel) {
        QueryWrapper<BizLabelDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("biz_type", bizLabel.getBizType());
        queryWrapper.eq("target_id", bizLabel.getTargetId());
        return bizLabelMapper.delete(queryWrapper);
    }

    @Override
    public List<BizLabel> findByTargetIds(List<Long> targetIds) {
        LambdaQueryWrapper<BizLabelDO> lambdaQueryWrapper = new LambdaQueryWrapper<>();
        lambdaQueryWrapper.in(BizLabelDO::getTargetId, targetIds);
        List<BizLabelDO> bizLabelDOS = bizLabelMapper.selectList(lambdaQueryWrapper);
        return CollectionUtils.isEmpty(bizLabelDOS) ? List.of() : BeanUtil.copyToList(bizLabelDOS, BizLabel.class);
    }

    @Override
    public List<BizLabel> findHistoryOfKbLabel(Long kbId) {
        List<BizLabelDO> historyOfKbLabel = bizLabelMapper.findHistoryOfKbLabel(kbId);
        return BeanUtil.copyToList(historyOfKbLabel, BizLabel.class);
    }

    @Override
    public List<BizLabel> findByKbNames(List<String> kbNames) {
        List<BizLabelDO> bizLabelDOS = bizLabelMapper.findByKbNames(kbNames);
        return BeanUtil.copyToList(bizLabelDOS, BizLabel.class);
    }

    @Override
    public List<BizLabel> findLabelByFileIdsAndFolderIds(List<Long> fileIds, List<Long> folderIds) {
        if (CollectionUtils.isEmpty(fileIds) && CollectionUtils.isEmpty(folderIds)) {
            return List.of();
        }
        List<BizLabelDO> bizLabels = bizLabelMapper.findLabelByFileIdsAndFolderIds(fileIds, folderIds);
        return CollectionUtils.isEmpty(bizLabels) ? List.of() : BeanUtil.copyToList(bizLabels, BizLabel.class);
    }

    @Override
    public List<BizLabel> findLabelByTargetIds(List<Long> targetIds) {
        List<BizLabelDO> bizLabelDOS = bizLabelMapper.findLabelByTargetIds(targetIds);
        return CollectionUtils.isEmpty(bizLabelDOS) ? List.of() : BeanUtil.copyToList(bizLabelDOS, BizLabel.class);
    }
}
