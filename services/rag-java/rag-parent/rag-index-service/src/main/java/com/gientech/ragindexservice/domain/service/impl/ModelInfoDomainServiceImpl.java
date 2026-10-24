package com.gientech.ragindexservice.domain.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.enmus.ModelStatusEnums;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragindexservice.domain.entity.ModelInfo;
import com.gientech.ragindexservice.domain.entity.ModelSimpInfo;
import com.gientech.ragindexservice.domain.repository.ModelInfoRepository;
import com.gientech.ragindexservice.domain.service.ModelInfoDomainService;
import jodd.util.StringUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Objects;

/**
 * @Desc 模型管理 服务实现类
 * @Author ZhenPanHong
 * @Date 2025/3/5 14:27
 */
@Service
public class ModelInfoDomainServiceImpl implements ModelInfoDomainService {

    @Autowired
    private ModelInfoRepository modelInfoRepository;

    @Override
    public ModelInfo addModelInfo(ModelInfo modelInfo) {
        Long id = modelInfoRepository.addModelInfo(modelInfo);
        modelInfo.setId(id);
        return modelInfo;
    }

    @Override
    public Boolean deleteById(Long id) {
        return modelInfoRepository.deleteById(id);
    }

    @Override
    public Boolean updateById(ModelInfo modelInfo) {
        return modelInfoRepository.updateById(modelInfo);
    }

    @Override
    public ModelInfo getById(Long id) {
        return modelInfoRepository.getById(id);
    }

    @Override
    public Page<ModelInfo> page(ModelInfo modelInfoParam, Long pageNo, Long pageSize) {
        return modelInfoRepository.page(modelInfoParam, pageNo, pageSize);
    }

    @Override
    public List<ModelInfo> list(ModelInfo modelInfoParam) {
        return modelInfoRepository.list(modelInfoParam);
    }

    @Override
    public Boolean existsById(Long id) {
        return exists(ModelInfo.builder().id(id).build());
    }

    @Override
    public Boolean existsByModelName(String modelName) {
        return exists(ModelInfo.builder().modelName(modelName).build());
    }

    @Override
    public Boolean existsByModelIde(String modelIde) {
        return exists(ModelInfo.builder().modelIde(modelIde).build());
    }

    @Override
    public Boolean exists(ModelInfo modelInfoParam) {
        return exists(modelInfoParam, Boolean.FALSE);
    }

    @Override
    public Boolean exists(ModelInfo modelInfoParam, Boolean isOr) {
        return modelInfoRepository.exists(modelInfoParam, isOr);
    }

    @Override
    public Page<ModelInfo> allPage(ModelInfo queryParam, Long pageNo, Long pageSize) {
        return modelInfoRepository.allPage(queryParam, pageNo, pageSize);
    }

    @Override
    public ModelInfo getByModelName(String modelName) {
        return modelInfoRepository.getByModelName(modelName);
    }

    @Override
    public ModelSimpInfo getSimpByModeName(String modeName) {
        ModelInfo modelInfo = modelInfoRepository.getByModelName(modeName);
        if (Objects.isNull(modelInfo))
            throw new ApplicationException(ErrCodeEnum.MODEL_NOT_EXIST, modeName);
        if (ModelStatusEnums.UNAVAILABLE.getCode().equals(modelInfo.getStatus()))
            throw new ApplicationException(ErrCodeEnum.MODEL_NOT_AVAILABLE, modeName);
        ModelSimpInfo modelSimpInfo = BeanUtil.copyProperties(modelInfo, ModelSimpInfo.class);
        if (StringUtil.isEmpty(modelSimpInfo.getApiKey()))
            modelSimpInfo.setApiKey("");
        return modelSimpInfo;
    }

    @Override
    public String queryCreator(Long id) {
        ModelInfo modelInfo = modelInfoRepository.getById(id);
        return Objects.isNull(modelInfo) ? null : modelInfo.getCreateBy();
    }

    @Override
    public Boolean transferProperty(String owner, String receiver) {
        return modelInfoRepository.transferProperty(owner, receiver) > 0;
    }

    @Override
    public ModelInfo getByModeIde(String modeIde) {
        return modelInfoRepository.getByModeIde(modeIde);
    }
}
