package com.gientech.ragindexservice.domain.repository;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragindexservice.domain.entity.ModelInfo;

import java.util.List;

/**
 * @Desc 模型信息 存储类
 * @Author ZhenPanHong
 * @Date 2025/3/5 13:32
 */
public interface ModelInfoRepository {

    /**
     * 新增模型信息
     *
     * @param modelInfo
     * @return
     */
    Long addModelInfo(ModelInfo modelInfo);

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
     * 通过模型名称查询数据
     * @param modelName
     * @return
     */
    ModelInfo getByModelName(String modelName);

    int transferProperty(String owner, String receiver);

    ModelInfo getByModeIde(String modeIde);
}
