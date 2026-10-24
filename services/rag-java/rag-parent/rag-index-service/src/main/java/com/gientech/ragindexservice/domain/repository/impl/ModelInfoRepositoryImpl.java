package com.gientech.ragindexservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollUtil;
import cn.hutool.core.util.StrUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.auth.enums.IsDtlEnums;
import com.gientech.ragcommon.index.enmus.ModelIsDelEnums;
import com.gientech.ragindexservice.domain.entity.ModelInfo;
import com.gientech.ragindexservice.domain.mapper.ModelInfoMapper;
import com.gientech.ragindexservice.domain.model.ModelInfoDO;
import com.gientech.ragindexservice.domain.repository.ModelInfoRepository;
import com.google.common.collect.Lists;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;

import java.util.List;
import java.util.Objects;

/**
 * @Desc 模型管理
 * @Author ZhenPanHong
 * @Date 2025/3/5 14:24
 */
@Repository
@Slf4j
public class ModelInfoRepositoryImpl implements ModelInfoRepository {

    @Autowired
    private ModelInfoMapper modelInfoMapper;

    @Override
    public Long addModelInfo(ModelInfo modelInfo) {
        ModelInfoDO modelInfoDO = BeanUtil.copyProperties(modelInfo, ModelInfoDO.class);
        modelInfoMapper.insert(modelInfoDO);
        return modelInfoDO.getId();
    }

    @Override
    public Boolean deleteById(Long id) {
        return modelInfoMapper.deleteById(id) > 0;
    }

    @Override
    public Boolean updateById(ModelInfo modelInfo) {
        ModelInfoDO modelInfoDO = BeanUtil.copyProperties(modelInfo, ModelInfoDO.class);
        return modelInfoMapper.updateById(modelInfoDO) > 0;
    }

    @Override
    public ModelInfo getById(Long id) {
        LambdaQueryWrapper<ModelInfoDO> wrapper = Wrappers.lambdaQuery(ModelInfoDO.class);
        wrapper.eq(ModelInfoDO::getIsDtl, IsDtlEnums.NO.getCode())
                .eq(ModelInfoDO::getId,id)
                .last("limit 1");
        ModelInfoDO modelInfoDO = modelInfoMapper.selectOne(wrapper);
        return Objects.isNull(modelInfoDO) ? null : BeanUtil.copyProperties(modelInfoDO, ModelInfo.class);
    }

    @Override
    public Page<ModelInfo> page(ModelInfo modelInfoParam, Long pageNo, Long pageSize) {
        LambdaQueryWrapper<ModelInfoDO> wrapper = Wrappers.lambdaQuery(ModelInfoDO.class)
                .eq(StrUtil.isNotBlank(modelInfoParam.getModelName()), ModelInfoDO::getModelName, modelInfoParam.getModelName())
                .eq(StrUtil.isNotBlank(modelInfoParam.getModelIde()), ModelInfoDO::getModelIde, modelInfoParam.getModelIde())
                .eq(Objects.nonNull(modelInfoParam.getType()), ModelInfoDO::getType, modelInfoParam.getType())
                .eq(Objects.nonNull(modelInfoParam.getStatus()), ModelInfoDO::getStatus, modelInfoParam.getStatus())
                .eq(Objects.nonNull(modelInfoParam.getCreateBy()), ModelInfoDO::getCreateBy, modelInfoParam.getCreateBy())
                .eq(StrUtil.isNotBlank(modelInfoParam.getModelName()), ModelInfoDO::getModelName, modelInfoParam.getModelName())
                .in(CollUtil.isNotEmpty(modelInfoParam.getIdList()), ModelInfoDO::getId, modelInfoParam.getIdList())
                .orderByDesc(ModelInfoDO::getGmtCreate);
        Page<ModelInfoDO> page = new Page<>(pageNo, pageSize);
        Page<ModelInfoDO> pageResult = modelInfoMapper.selectPage(page, wrapper);
        Page<ModelInfo> modelInfoPage = new Page<>();
        BeanUtil.copyProperties(pageResult, modelInfoPage);
        List<ModelInfo> modelInfoList = BeanUtil.copyToList(pageResult.getRecords(), ModelInfo.class);
        modelInfoPage.setRecords(modelInfoList);
        return modelInfoPage;


    }

    @Override
    public List<ModelInfo> list(ModelInfo modelInfoParam) {
        LambdaQueryWrapper<ModelInfoDO> wrapper = Wrappers.lambdaQuery(ModelInfoDO.class)
                .eq(StrUtil.isNotBlank(modelInfoParam.getModelName()), ModelInfoDO::getModelName, modelInfoParam.getModelName())
                .eq(StrUtil.isNotBlank(modelInfoParam.getModelIde()), ModelInfoDO::getModelIde, modelInfoParam.getModelIde())
                .eq(Objects.nonNull(modelInfoParam.getType()), ModelInfoDO::getType, modelInfoParam.getType())
                .eq(Objects.nonNull(modelInfoParam.getStatus()), ModelInfoDO::getStatus, modelInfoParam.getStatus())
                .eq(Objects.nonNull(modelInfoParam.getCreateBy()), ModelInfoDO::getCreateBy, modelInfoParam.getCreateBy())
                .ne(ModelInfoDO::getIsDtl, ModelIsDelEnums.DELETE.getCode())
                .orderByDesc(ModelInfoDO::getGmtCreate);
        List<ModelInfoDO> modelInfoDOS = modelInfoMapper.selectList(wrapper);
        return BeanUtil.copyToList(modelInfoDOS, ModelInfo.class);
    }

    @Override
    public Boolean exists(ModelInfo modelInfoParam, Boolean isOr) {
        LambdaQueryWrapper<ModelInfoDO> wrapper = Wrappers.lambdaQuery(ModelInfoDO.class);
        if (isOr) {
            wrapper = wrapper
                    .or(w -> w.eq(Objects.nonNull(modelInfoParam.getId()), ModelInfoDO::getId, modelInfoParam.getId()))
                    .or(w -> w.eq(StrUtil.isNotBlank(modelInfoParam.getModelName()), ModelInfoDO::getModelName, modelInfoParam.getModelName()))
                    .or(w -> w.eq(StrUtil.isNotBlank(modelInfoParam.getModelIde()), ModelInfoDO::getModelIde, modelInfoParam.getModelIde()))
                    .or(w -> w.eq(Objects.nonNull(modelInfoParam.getType()), ModelInfoDO::getType, modelInfoParam.getType()))
                    .or(w -> w.eq(Objects.nonNull(modelInfoParam.getStatus()), ModelInfoDO::getStatus, modelInfoParam.getStatus()));
        } else {
            wrapper = wrapper
                    .eq(Objects.nonNull(modelInfoParam.getId()), ModelInfoDO::getId, modelInfoParam.getId())
                    .eq(StrUtil.isNotBlank(modelInfoParam.getModelName()), ModelInfoDO::getModelName, modelInfoParam.getModelName())
                    .eq(StrUtil.isNotBlank(modelInfoParam.getModelIde()), ModelInfoDO::getModelIde, modelInfoParam.getModelIde())
                    .eq(Objects.nonNull(modelInfoParam.getType()), ModelInfoDO::getType, modelInfoParam.getType())
                    .eq(Objects.nonNull(modelInfoParam.getStatus()), ModelInfoDO::getStatus, modelInfoParam.getStatus());
        }
        return modelInfoMapper.exists(wrapper);

    }

    @Override
    public Page<ModelInfo> allPage(ModelInfo queryParam, Long pageNo, Long pageSize) {
        Page<ModelInfoDO> modelInfoDOPage = new Page<>(pageNo, pageSize);
        modelInfoMapper.allPage(modelInfoDOPage, queryParam);
        Page<ModelInfo> modelInfoPage = new Page<>();
        BeanUtil.copyProperties(modelInfoDOPage, modelInfoPage);
        List<ModelInfo> modelInfoList = BeanUtil.copyToList(modelInfoDOPage.getRecords(), ModelInfo.class);
        modelInfoPage.setRecords(modelInfoList);
        return modelInfoPage;
    }

    @Override
    public ModelInfo getByModelName(String modelName) {
        QueryWrapper<ModelInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("model_name", modelName)
                .eq("is_dtl", 0)
                .last("limit 1");
        ModelInfoDO modelInfoDO = modelInfoMapper.selectOne(queryWrapper);
        return Objects.isNull(modelInfoDO) ? null : BeanUtil.copyProperties(modelInfoDO, ModelInfo.class);
    }

    @Override
    public int transferProperty(String owner, String receiver) {
        QueryWrapper<ModelInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("create_by", owner);
        queryWrapper.eq("is_dtl", 0);
        List<ModelInfoDO> modelInfoDOS = modelInfoMapper.selectList(queryWrapper);
        if (!CollectionUtils.isEmpty(modelInfoDOS)) {
            List<Long> ids = modelInfoDOS.stream().map(ModelInfoDO::getId).toList();
            modelInfoMapper.updateCreator(ids, receiver);
        }
        return 0;
    }

    @Override
    public ModelInfo getByModeIde(String modeIde) {
        LambdaQueryWrapper<ModelInfoDO> queryWrapper = Wrappers.lambdaQuery(ModelInfoDO.class)
                .eq(ModelInfoDO::getModelIde, modeIde)
                .last("limit 1");
        ModelInfoDO modelInfoDO = modelInfoMapper.selectOne(queryWrapper);
        return Objects.isNull(modelInfoDO) ? null : BeanUtil.copyProperties(modelInfoDO, ModelInfo.class);
    }
}
