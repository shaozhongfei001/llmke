package com.gientech.ragindexservice.domain.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragindexservice.domain.entity.ModelSimpInfo;
import com.gientech.ragindexservice.domain.entity.ModelInfo;

import java.util.List;

/**
 * @Desc 模型信息 服务类
 * @Author ZhenPanHong
 * @Date 2025/3/5 14:25
 */
public interface ModelInfoDomainService {
    /**
     * 创建模型信息
     *
     * @param modelInfo
     * @return
     */
    ModelInfo addModelInfo(ModelInfo modelInfo);

    /**
     * 根据ID删除模型信息
     *
     * @param id
     * @return
     */
    Boolean deleteById(Long id);

    /**
     * 根据ID更新模型信息
     *
     * @param modelInfo
     * @return
     */
    Boolean updateById(ModelInfo modelInfo);

    /**
     * 根据id查询模型信息
     *
     * @param id
     * @return
     */
    ModelInfo getById(Long id);

    /**
     * 分页查询模型信息
     *
     * @param modelInfoParam
     * @param pageNo
     * @param pageSize
     * @return
     */
    Page<ModelInfo> page(ModelInfo modelInfoParam, Long pageNo, Long pageSize);

    /**
     * 查询模型信息列表
     *
     * @param modelInfoParam
     * @return
     */
    List<ModelInfo> list(ModelInfo modelInfoParam);

    /**
     * 根据ID校验模型是否存在
     *
     * @param id
     * @return
     */
    Boolean existsById(Long id);

    /**
     * 根据模型名称校验模型是否存在
     *
     * @param modelName
     * @return
     */
    Boolean existsByModelName(String modelName);

    /**
     * 根据待接入模型的ID校验模型是否存在
     *
     * @param modelIde
     * @return
     */
    Boolean existsByModelIde(String modelIde);

    /**
     * 检验是否有符合条件的模型存在
     *
     * @param modelInfoParam
     * @return
     */
    Boolean exists(ModelInfo modelInfoParam);

    /**
     * 检验是否有符合条件的模型存在
     *
     * @param modelInfoParam
     * @param isOr           各条件关系是否为or
     * @return
     */
    Boolean exists(ModelInfo modelInfoParam, Boolean isOr);

    /**
     * 自建和共享模型列表数据(分页)
     *
     * @param queryParam
     * @param pageNo
     * @param pageSize
     * @return
     */
    Page<ModelInfo> allPage(ModelInfo queryParam, Long pageNo, Long pageSize);

    /**
     * 通过模型名称查询
     *
     * @param modeName
     * @return
     */
    ModelInfo getByModelName(String modeName);

    ModelSimpInfo getSimpByModeName(String modeName);

    String queryCreator(Long id);

    Boolean transferProperty(String owner, String receiver);

    /**
     * 根据待接入的模型id查询
     * @param modeIde
     * @return
     */
    ModelInfo getByModeIde(String modeIde);
}
