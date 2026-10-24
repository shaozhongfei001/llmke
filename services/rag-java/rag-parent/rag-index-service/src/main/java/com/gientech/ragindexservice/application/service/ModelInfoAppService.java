package com.gientech.ragindexservice.application.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.dto.ModelInfoDTO;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import com.gientech.ragcommon.index.request.ModelInfoCreateReq;
import com.gientech.ragcommon.index.request.ModelInfoQueryReq;
import com.gientech.ragcommon.index.request.ModelInfoUpdateReq;
import com.gientech.ragindexservice.domain.entity.ModelSimpInfo;

import java.util.List;
import java.util.Map;

/**
 * @Desc 模型信息 服务类
 * @Author ZhenPanHong
 * @Date 2025/3/5 14:29
 */
public interface ModelInfoAppService {

    /**
     * 创建模型信息
     *
     * @param modelInfoCreateReq
     * @return
     */
    ModelInfoDTO createModelInfo(ModelInfoCreateReq modelInfoCreateReq);

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
     * @param modelInfoUpdateReq
     * @return
     */
    ModelInfoDTO updateById(ModelInfoUpdateReq modelInfoUpdateReq);


    /**
     * 根据id查询模型信息
     *
     * @param id
     * @return
     */
    ModelInfoDTO getById(Long id);

    /**
     * 分页查询模型信息
     *
     * @param modelInfoQueryReq
     * @return
     */
    Page<ModelInfoDTO> page(ModelInfoQueryReq modelInfoQueryReq);

    /**
     * 查询模型信息列表
     *
     * @param modelInfoQueryReq
     * @return
     */
    List<ModelInfoDTO> list(ModelInfoQueryReq modelInfoQueryReq);

    /**
     * 获取模型类型集合
     *
     * @return
     */
    List<Map> getModelTypes();

    /**
     * 共享模型列表数据(分页)
     *
     * @param modelInfoQueryReq
     * @return
     */
    Page<ModelInfoDTO> sharePage(ModelInfoQueryReq modelInfoQueryReq);

    /**
     * 自建和共享模型列表数据(分页)
     *
     * @param modelInfoQueryReq
     * @return
     */
    Page<ModelInfoDTO> allPage(ModelInfoQueryReq modelInfoQueryReq);

    /**
     * 通过模型名称查询模型详情
     *
     * @param modeName
     * @return
     */
    ModelInfoDTO getByModelName(String modeName);

    /**
     * 查询模型创建者
     *
     * @param id
     * @return
     */
    String queryCreator(Long id);

    Boolean transferProperty(String owner, String receiver);

    ModelSimpInfo getModelByType(Integer type);

    ModelSimpDTO getSimpByModeName(String modeName);

    ModelSimpDTO getSimpByModeName(String modeName, boolean needAuth);

    ModelSimpDTO getByModeName(String modeName);

    ModelSimpDTO getByModeName(String modeName, boolean needAuth);

    List<Map> getModelProtocols();

    Boolean check();

    Boolean replaceModel(Long sourceModelId, Long targetModelId);

    Integer getStatusById(Long id);

    int checkModelReference(String modelName);
}
