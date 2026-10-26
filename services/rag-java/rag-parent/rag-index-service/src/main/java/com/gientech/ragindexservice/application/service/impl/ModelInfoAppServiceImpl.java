package com.gientech.ragindexservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollUtil;
import cn.hutool.core.util.StrUtil;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.fastjson2.JSONWriter;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.auth.dto.PrivilegeDTO;
import com.gientech.ragcommon.auth.enums.PrivilegeTypeEnums;
import com.gientech.ragcommon.auth.enums.RoleTypeEnums;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.dto.ModelInfoDTO;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import com.gientech.ragcommon.index.enmus.ModelStatusEnums;
import com.gientech.ragcommon.index.enmus.ModelTypeEnums;
import com.gientech.ragcommon.index.enmus.PermissionEnums;
import com.gientech.ragcommon.index.request.ModelInfoCreateReq;
import com.gientech.ragcommon.index.request.ModelInfoQueryReq;
import com.gientech.ragcommon.index.request.ModelInfoUpdateReq;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragindexservice.application.remote.PrivilegeClient;
import com.gientech.ragindexservice.application.remote.SearchConfigClient;
import com.gientech.ragindexservice.application.remote.UserClient;
import com.gientech.ragindexservice.application.service.KnowledgeBaseAppService;
import com.gientech.ragindexservice.application.service.ModelInfoAppService;
import com.gientech.ragindexservice.domain.entity.ModelInfo;
import com.gientech.ragindexservice.domain.entity.ModelSimpInfo;
import com.gientech.ragindexservice.domain.service.ModelInfoDomainService;
import com.gientech.ragindexservice.infrastructure.IndexNacosConfig;
import com.gientech.ragindexservice.infrastructure.RemoteFileUtils;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;

import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.stream.Collectors;

import static com.gientech.ragcommon.index.enmus.ModelStatusEnums.CHECK_ING;

@Slf4j
@Service
public class ModelInfoAppServiceImpl implements ModelInfoAppService {

    @Autowired
    private ModelInfoDomainService modelInfoDomainService;

    @Autowired
    public IndexNacosConfig indexNacosConfig;

    @Autowired
    private PrivilegeClient privilegeClient;

    @Autowired
    private RemoteFileUtils remoteFileUtils;

    @Autowired
    private UserClient userClient;

    @Autowired
    private SearchConfigClient searchConfigClient;


    private static ExecutorService executorService = Executors.newFixedThreadPool(
            Runtime.getRuntime().availableProcessors() * 4 + Runtime.getRuntime().availableProcessors() / 2);

    @Autowired
    private KnowledgeBaseAppService knowledgeBaseAppService;


    @Override
    public ModelInfoDTO createModelInfo(ModelInfoCreateReq modelInfoCreateReq) {
        // 保存前校验
        validateBeforeSave(modelInfoCreateReq);

        // 检测联通性,如果符合标准,将状态设置为可用,否则不可用
        ModelInfo modelInfo = BeanUtil.copyProperties(modelInfoCreateReq, ModelInfo.class);
        updateModelStatus(modelInfo);

        // 保存模型信息到数据库
        modelInfoDomainService.addModelInfo(modelInfo);
        return BeanUtil.copyProperties(modelInfo, ModelInfoDTO.class);
    }

    @Override
    public Boolean deleteById(Long id) {
        // 删除前校验
        validateBeforeDelete(id);

        // 根据ID删除模型信息
        return modelInfoDomainService.deleteById(id);
    }

    @Override
    public ModelInfoDTO updateById(ModelInfoUpdateReq modelInfoUpdateReq) {
        // 更新前校验
        validateBeforeUpdate(modelInfoUpdateReq);

        // 检测联通性,如果符合标准,将状态设置为可用,否则不可用
        ModelInfo modelInfo = BeanUtil.copyProperties(modelInfoUpdateReq, ModelInfo.class);
        updateModelStatus(modelInfo);

        //更新助手配置的溯源
//        Boolean needTrace = modelInfoUpdateReq.getTrace();
        Boolean thinking = modelInfoUpdateReq.getThinking() == null ? Boolean.FALSE : modelInfoUpdateReq.getThinking();
        searchConfigClient.updateModelConfig(modelInfoUpdateReq.getModelName(), thinking);

        // 更新模型信息到数据库
        modelInfoDomainService.updateById(modelInfo);
        return BeanUtil.copyProperties(modelInfo, ModelInfoDTO.class);
    }

    @Override
    public List<Map> getModelTypes() {
        // 从Nacos配置中获取模型类型列表
        return JSON.parseArray(indexNacosConfig.getDefaultModelTypes(), Map.class);
    }

    @Override
    public Page<ModelInfoDTO> sharePage(ModelInfoQueryReq modelInfoQueryReq) {
        // 获取当前用户的模型权限列表
        List<PrivilegeDTO> permissionList = privilegeClient.getAllPermission(PrivilegeTypeEnums.MODEL.getCode(), null);
        if (CollectionUtils.isEmpty(permissionList)) {
            return new Page<>();
        }
        // 获取相关的模型基本信息
        List<Long> modelIds = permissionList.stream().map(PrivilegeDTO::getTargetId).toList();
        ModelInfo queryParam = BeanUtil.copyProperties(modelInfoQueryReq, ModelInfo.class);
        queryParam.setIdList(modelIds);
        Page<ModelInfo> modelInfoPage = modelInfoDomainService.page(queryParam, modelInfoQueryReq.getPageNo(), modelInfoQueryReq.getPageSize());
        Page<ModelInfoDTO> modelInfoDTOPage = new Page<>();
        BeanUtil.copyProperties(modelInfoPage, modelInfoDTOPage);
        List<ModelInfoDTO> modelInfoDTOList = BeanUtil.copyToList(modelInfoPage.getRecords(), ModelInfoDTO.class);
        modelInfoDTOPage.setRecords(modelInfoDTOList);

        if (CollUtil.isEmpty(modelInfoDTOList))
            return modelInfoDTOPage;

        // 构建模型ID到权限的映射
        Map<Long, Integer> permissionMap = permissionList.stream().collect(Collectors.toMap(PrivilegeDTO::getTargetId, PrivilegeDTO::getPermission));
        // 为每个模型信息DTO设置对应的权限
        for (ModelInfoDTO modelInfoDTO : modelInfoDTOList) {
            if (permissionMap.containsKey(modelInfoDTO.getId()))
                modelInfoDTO.setPermission(permissionMap.get(modelInfoDTO.getId()));
        }
        return modelInfoDTOPage;
    }

    @Override
    public Page<ModelInfoDTO> allPage(ModelInfoQueryReq modelInfoQueryReq) {
        ModelInfo queryParam = BeanUtil.copyProperties(modelInfoQueryReq, ModelInfo.class);
        User user = UserContext.getUser();
        String apiKey = user.getApiKey();
        if (!modelInfoQueryReq.isNeedAuth() || StringUtils.hasText(apiKey) || RoleTypeEnums.SUPER_ADMIN.getCode().equals(userClient.getUserType())) {
            Page<ModelInfo> modelInfoPage = modelInfoDomainService.page(queryParam, modelInfoQueryReq.getPageNo(), modelInfoQueryReq.getPageSize());
            Page<ModelInfoDTO> modelInfoDTOPage = new Page<>();
            BeanUtil.copyProperties(modelInfoPage, modelInfoDTOPage);
            List<ModelInfo> modelInfoList = modelInfoPage.getRecords();
            List<ModelInfoDTO> modelInfoDTOList = BeanUtil.copyToList(modelInfoList, ModelInfoDTO.class);
            modelInfoDTOList.forEach(modelInfoDTO -> modelInfoDTO.setPermission(PermissionEnums.ALL.getCode()));
            modelInfoDTOPage.setRecords(modelInfoDTOList);
            return modelInfoDTOPage;
        }


        // 获取当前用户的模型权限列表
        List<PrivilegeDTO> permissionList = privilegeClient.getAllPermission(PrivilegeTypeEnums.MODEL.getCode(), null);
        String userName = UserContext.getUser().getUserName();
        queryParam.setCreateBy(userName);
        queryParam.setIdList(permissionList.stream().map(PrivilegeDTO::getTargetId).toList());

        Page<ModelInfo> modelInfoPage = modelInfoDomainService.allPage(queryParam, modelInfoQueryReq.getPageNo(), modelInfoQueryReq.getPageSize());
        Page<ModelInfoDTO> modelInfoDTOPage = new Page<>();
        BeanUtil.copyProperties(modelInfoPage, modelInfoDTOPage);
        List<ModelInfo> modelInfoList = modelInfoPage.getRecords();
        List<ModelInfoDTO> modelInfoDTOList = BeanUtil.copyToList(modelInfoList, ModelInfoDTO.class);
        modelInfoDTOPage.setRecords(modelInfoDTOList);

        if (CollUtil.isEmpty(modelInfoDTOList))
            return modelInfoDTOPage;

        // 模型权限赋值,且优先级:自建 > 共享
        Map<Long, Integer> permissionMap = permissionList.stream().collect(Collectors.toMap(PrivilegeDTO::getTargetId, PrivilegeDTO::getPermission));
        Map<Long, String> createByMap = modelInfoList.stream().collect(Collectors.toMap(ModelInfo::getId, ModelInfo::getCreateBy));

        for (ModelInfoDTO modelInfoDTO : modelInfoDTOList) {
            if (permissionMap.containsKey(modelInfoDTO.getId()))
                modelInfoDTO.setPermission(permissionMap.get(modelInfoDTO.getId()));
            if (createByMap.containsKey(modelInfoDTO.getId()) && userName.equals(createByMap.get(modelInfoDTO.getId())))
                modelInfoDTO.setPermission(PermissionEnums.ALL.getCode());
        }
        return modelInfoDTOPage;
    }

    @Override
    public ModelInfoDTO getById(Long id) {
        // 根据ID获取模型信息
        ModelInfo modelInfo = modelInfoDomainService.getById(id);
        return Objects.isNull(modelInfo) ? null : BeanUtil.copyProperties(modelInfo, ModelInfoDTO.class);
    }

    @Override
    public Page<ModelInfoDTO> page(ModelInfoQueryReq modelInfoQueryReq) {
        // 根据查询条件分页获取模型信息
        ModelInfo modelInfoParam = BeanUtil.copyProperties(modelInfoQueryReq, ModelInfo.class);
        modelInfoParam.setCreateBy(UserContext.getUser().getUserName());
        Page<ModelInfo> modelInfoPage = modelInfoDomainService.page(modelInfoParam, modelInfoQueryReq.getPageNo(), modelInfoQueryReq.getPageSize());
        Page<ModelInfoDTO> modelInfoDTOPage = new Page<>();
        BeanUtil.copyProperties(modelInfoPage, modelInfoDTOPage);
        List<ModelInfoDTO> modelInfoDTOList = BeanUtil.copyToList(modelInfoPage.getRecords(), ModelInfoDTO.class);
        modelInfoDTOPage.setRecords(modelInfoDTOList);
        return modelInfoDTOPage;
    }

    @Override
    public List<ModelInfoDTO> list(ModelInfoQueryReq modelInfoQueryReq) {
        // 根据查询条件获取模型信息列表
        ModelInfo modelInfoParam = BeanUtil.copyProperties(modelInfoQueryReq, ModelInfo.class);
        modelInfoParam.setCreateBy(UserContext.getUser().getUserName());
        List<ModelInfo> modelInfoList = modelInfoDomainService.list(modelInfoParam);
        return BeanUtil.copyToList(modelInfoList, ModelInfoDTO.class);
    }


    /**
     * 保存前校验
     *
     * @param modelInfoCreateReq 创建模型的请求对象
     */
    private void validateBeforeSave(ModelInfoCreateReq modelInfoCreateReq) {
        String type = getType(modelInfoCreateReq.getType());
        String modelName = modelInfoCreateReq.getModelName();
        String modelIde = modelInfoCreateReq.getModelIde();

        if (StrUtil.isBlank(type))
            throw new ApplicationException(ErrCodeEnum.MODEL_TYPE_NOT_FOUND);

        ModelInfo dbModelInfoByModeName = modelInfoDomainService.getByModelName(modelName);
        if (Objects.nonNull(dbModelInfoByModeName))
            throw new ApplicationException(dbModelInfoByModeName.getCreateBy() + "用户已经创建该模型,不允许重复");

        ModelInfo dbModelInfoByModeIde = modelInfoDomainService.getByModeIde(modelIde);
        if (Objects.nonNull(dbModelInfoByModeIde))
            throw new ApplicationException(dbModelInfoByModeIde.getCreateBy() + "用户已使用该模型ID，不允许重复使用");

    }

    /**
     * 更新前校验
     *
     * @param modelInfoUpdateReq 更新模型的请求对象
     */
    private void validateBeforeUpdate(ModelInfoUpdateReq modelInfoUpdateReq) {
        Long id = modelInfoUpdateReq.getId();
        String modelName = modelInfoUpdateReq.getModelName();
        String modelIde = modelInfoUpdateReq.getModelIde();

        ModelInfo dbModelInfo = modelInfoDomainService.getById(id);
        String type = getType(modelInfoUpdateReq.getType());

        if (StrUtil.isBlank(type))
            throw new ApplicationException(ErrCodeEnum.MODEL_TYPE_NOT_FOUND);

        if (Objects.isNull(dbModelInfo))
            throw new ApplicationException(ErrCodeEnum.MODEL_NOT_EXIST);

        if (!dbModelInfo.getModelName().equals(modelName)) {
            ModelInfo dbModelInfoByModeName = modelInfoDomainService.getByModelName(modelName);
            if (Objects.nonNull(dbModelInfoByModeName))
                throw new ApplicationException(dbModelInfoByModeName.getCreateBy() + "用户已经创建该模型,不允许重复");
        }

        if (!dbModelInfo.getModelIde().equals(modelIde)) {
            ModelInfo dbModelInfoByModeIde = modelInfoDomainService.getByModeIde(modelIde);
            if (Objects.nonNull(dbModelInfoByModeIde))
                throw new ApplicationException(dbModelInfoByModeIde.getCreateBy() + "用户已使用该模型ID，不允许重复使用");
        }

    }

    private void validateBeforeDelete(Long id) {
        if (Objects.isNull(id) || id <= 0)
            throw new ApplicationException(ErrCodeEnum.MODEL_ID_FORMAT_ERROR);
        if (!modelInfoDomainService.existsById(id))
            throw new ApplicationException(ErrCodeEnum.MODEL_NOT_EXIST);
    }

    /**
     * 获取模型类型标签
     *
     * @param type 模型类型ID
     * @return 模型类型标签
     */
    private String getType(Integer type) {
        List<Map> modelTypes = getModelTypes();
        return modelTypes.stream()
                .filter(modelType -> String.valueOf(type).equals(modelType.get("value")))
                .map(modelType -> (String) modelType.get("label"))
                .findFirst()
                .orElse(null);
    }

    /**
     * 根据模型联通性更新模型状态
     *
     * @param modelInfo 模型信息对象
     */
    private void updateModelStatus(ModelInfo modelInfo) {
        modelInfo.setStatus(checkConnectivity(modelInfo) ? ModelStatusEnums.AVAILABLE.getCode() : ModelStatusEnums.UNAVAILABLE.getCode());
    }

    /**
     * 检测模型的联通性
     *
     * @param modelInfo 模型信息对象
     * @return 如果模型联通返回true，否则返回false
     */
    private boolean checkConnectivity(ModelInfo modelInfo) {
        JSONObject modelCheckReq = new JSONObject();
        JSONObject modelInfoJson = new JSONObject();

        modelInfoJson.put("model_name", modelInfo.getModelName());
        modelInfoJson.put("url", modelInfo.getUrl());
        modelInfoJson.put("key", modelInfo.getApiKey());
        modelInfoJson.put("model_id", modelInfo.getModelIde());
        modelInfoJson.put("type", modelInfo.getType());

        modelCheckReq.put("model_info", modelInfoJson);

        String resp = remoteFileUtils.modelCheck(modelCheckReq.toJSONString(JSONWriter.Feature.WriteMapNullValue));
        JSONObject respJson = JSONObject.parseObject(resp);
        if (Objects.equals(respJson.getInteger("code"), 200)) {
            modelInfo.setErrorMsg(null);
            return true;
        } else {
            modelInfo.setErrorMsg(respJson.getString("msg"));
            return false;
        }
    }

    @Override
    public ModelInfoDTO getByModelName(String modeName) {
        ModelInfo modelInfo = modelInfoDomainService.getByModelName(modeName);
        if (Objects.isNull(modelInfo))
            throw new ApplicationException(ErrCodeEnum.MODEL_NOT_EXIST);
        if (ModelStatusEnums.UNAVAILABLE.getCode().equals(modelInfo.getStatus()))
            throw new ApplicationException(ErrCodeEnum.MODEL_NOT_AVAILABLE);
        return BeanUtil.copyProperties(modelInfo, ModelInfoDTO.class);
    }

    @Override
    public String queryCreator(Long id) {
        return modelInfoDomainService.queryCreator(id);
    }

    @Override
    public Boolean transferProperty(String owner, String receiver) {
        return modelInfoDomainService.transferProperty(owner, receiver);
    }

    @Override
    public ModelSimpInfo getModelByType(Integer type) {
        if (Objects.isNull(type))
            throw new ApplicationException(ErrCodeEnum.MODEL_TYPE_IS_NULL);
        ModelInfoQueryReq req = new ModelInfoQueryReq();
        req.setPageNo(1L);
        req.setPageSize(1L);
        req.setStatus(1);
        req.setType(type);
        Page<ModelInfoDTO> modelInfoDTOPage = allPage(req);
        List<ModelInfoDTO> records = modelInfoDTOPage.getRecords();
        return CollectionUtils.isEmpty(records) ? new ModelSimpInfo() : BeanUtil.copyProperties(records.get(0), ModelSimpInfo.class);

//        if(CollectionUtils.isEmpty(records))
//            throw new ApplicationException(ErrCodeEnum.MODEL_NOT_EXIST.getErrCode(),"您没有权限使用【"+ Objects.requireNonNull(ModelTypeEnums.geyByCode(type)).getDesc() +"】类型的模型，请联系管理员！");
//        return BeanUtil.copyProperties(records.get(0),ModelSimpInfo.class);
    }

    @Override
    public ModelSimpDTO getSimpByModeName(String modeName) {
//        return BeanUtil.copyProperties(modelInfoDomainService.getSimpByModeName(modeName),ModelSimpDTO.class);
        if (StringUtils.isEmpty(modeName))
            throw new ApplicationException(ErrCodeEnum.MODEL_TYPE_IS_NULL);
        ModelInfoQueryReq req = new ModelInfoQueryReq();
        req.setPageNo(1L);
        req.setPageSize(1L);
//        req.setStatus(1);
        req.setModelName(modeName);
        Page<ModelInfoDTO> modelInfoDTOPage;
        try {
            modelInfoDTOPage = allPage(req);
        } catch (RuntimeException ex) {
            // R13-FIX-QA-07：服务间（Feign）调用常发生在线程池/异步链路上，UserContext 为空，
            // allPage 的按主体过滤会因解析不到部门/机构而抛 "Cannot parse null string"。
            // 这类内部调用退化为"不按主体过滤"（对外仍由网关强制登录），否则整条问答会因为
            // 取不到 model_info 而退化成"模型暂时无法返回"。
            log.warn("getSimpByModeName scoped query failed ({}), fallback to unscoped", ex.getMessage());
            req.setNeedAuth(false);
            modelInfoDTOPage = allPage(req);
        }
        List<ModelInfoDTO> records = modelInfoDTOPage.getRecords();
        if (CollectionUtils.isEmpty(records))
            throw new ApplicationException(ErrCodeEnum.MODEL_NOT_EXIST.getErrCode(), "您没有权限使用【" + modeName + "】模型，请联系管理员！");
        ModelInfoDTO modelInfoDTO = records.get(0);
        if (ModelStatusEnums.UNAVAILABLE.getCode().equals(modelInfoDTO.getStatus()))
            throw new ApplicationException(ErrCodeEnum.MODEL_NOT_EXIST.getErrCode(), "【" + modeName + "】模型不可用，请联系管理员！");
        ModelSimpDTO modelSimpDTO = BeanUtil.copyProperties(modelInfoDTO, ModelSimpDTO.class);
        if (StringUtils.isEmpty(modelSimpDTO.getApiKey()))
            modelSimpDTO.setApiKey("");
        return modelSimpDTO;
    }

    @Override
    public ModelSimpDTO getSimpByModeName(String modeName, boolean needAuth) {
//        return BeanUtil.copyProperties(modelInfoDomainService.getSimpByModeName(modeName),ModelSimpDTO.class);
        if (StringUtils.isEmpty(modeName))
            throw new ApplicationException(ErrCodeEnum.MODEL_TYPE_IS_NULL);
        ModelInfoQueryReq req = new ModelInfoQueryReq();
        req.setPageNo(1L);
        req.setPageSize(1L);
//        req.setStatus(1);
        req.setModelName(modeName);
        req.setNeedAuth(needAuth);
        Page<ModelInfoDTO> modelInfoDTOPage = allPage(req);
        List<ModelInfoDTO> records = modelInfoDTOPage.getRecords();
        if (CollectionUtils.isEmpty(records))
            throw new ApplicationException(ErrCodeEnum.MODEL_NOT_EXIST.getErrCode(), "您没有权限使用【" + modeName + "】模型，请联系管理员！");
        ModelInfoDTO modelInfoDTO = records.get(0);
        if (ModelStatusEnums.UNAVAILABLE.getCode().equals(modelInfoDTO.getStatus()))
            throw new ApplicationException(ErrCodeEnum.MODEL_NOT_EXIST.getErrCode(), "【" + modeName + "】模型不可用，请联系管理员！");
        ModelSimpDTO modelSimpDTO = BeanUtil.copyProperties(modelInfoDTO, ModelSimpDTO.class);
        if (StringUtils.isEmpty(modelSimpDTO.getApiKey()))
            modelSimpDTO.setApiKey("");
        return modelSimpDTO;
    }

    @Override
    public ModelSimpDTO getByModeName(String modeName) {
        if (StringUtils.isEmpty(modeName))
            throw new ApplicationException(ErrCodeEnum.MODEL_NAME_IS_NULL);
        ModelInfoQueryReq req = new ModelInfoQueryReq();
        req.setPageNo(1L);
        req.setPageSize(1L);
        req.setStatus(1);
        req.setModelName(modeName);
        Page<ModelInfoDTO> modelInfoDTOPage = allPage(req);
        List<ModelInfoDTO> records = modelInfoDTOPage.getRecords();
        return CollectionUtils.isEmpty(records) ? null : BeanUtil.copyProperties(records.get(0), ModelSimpDTO.class);
    }

    @Override
    public ModelSimpDTO getByModeName(String modeName, boolean needAuth) {
        if (StringUtils.isEmpty(modeName))
            throw new ApplicationException(ErrCodeEnum.MODEL_NAME_IS_NULL);
        ModelInfoQueryReq req = new ModelInfoQueryReq();
        req.setPageNo(1L);
        req.setPageSize(1L);
        req.setStatus(1);
        req.setModelName(modeName);
        req.setNeedAuth(needAuth);
        Page<ModelInfoDTO> modelInfoDTOPage = allPage(req);
        List<ModelInfoDTO> records = modelInfoDTOPage.getRecords();
        return CollectionUtils.isEmpty(records) ? null : BeanUtil.copyProperties(records.get(0), ModelSimpDTO.class);
    }

    @Override
    public List<Map> getModelProtocols() {
        return JSON.parseArray(indexNacosConfig.getDefaultModelProtocols(), Map.class);
    }

    @Override
    public Boolean check() {
        //查询模型
        ModelInfo modelInfoParam = new ModelInfo();
        List<ModelInfo> modelInfoList = modelInfoDomainService.list(modelInfoParam);
        if (!CollectionUtils.isEmpty(modelInfoList)) {
            modelInfoList.forEach(modelInfo -> {
                executorService.execute(() -> {
                    try {
                        modelInfo.setStatus(CHECK_ING.getCode());
                        modelInfoDomainService.updateById(modelInfo);
                        //检测联通性,如果符合标准,将状态设置为可用,否则不可用
                        updateModelStatus(modelInfo);
                        modelInfoDomainService.updateById(modelInfo);
                    } catch (Exception e) {
                        log.error(e.getMessage());
                    }
                });
            });
        }

        return true;
    }

    @Override
    public Integer getStatusById(Long id) {
        // 根据ID获取模型信息
        ModelInfo modelInfo = modelInfoDomainService.getById(id);
        if (Objects.isNull(modelInfo))
            throw new ApplicationException(ErrCodeEnum.MODEL_NOT_EXIST);
        return modelInfo.getStatus();
    }

    @Override
    public Boolean replaceModel(Long sourceModelId, Long targetModelId) {
        ModelInfo sourceModel = modelInfoDomainService.getById(sourceModelId);
        ModelTypeEnums modelType = ModelTypeEnums.getByCode(sourceModel.getType());
        String taskUUID = UUID.randomUUID().toString();
        String sourceModelName = sourceModel.getModelName();
        ModelInfo targetModel = modelInfoDomainService.getById(targetModelId);
        String targetModelName = targetModel.getModelName();
        if (Objects.nonNull(modelType)) {
            //更新知识库
            Boolean updateKBSuccess = knowledgeBaseAppService.replaceModel(taskUUID, modelType.getFieldName(), sourceModelName, targetModelName);
            if (!updateKBSuccess) {
                log.error("替换知识库中的模型失败或影响0条, {} to {}", sourceModelName, targetModelName);
            }

            //更新助手
            Boolean updateConfigSuccess = searchConfigClient.replaceModel(sourceModelName, targetModelName);
            if (!updateConfigSuccess) {
                log.error("替换助手中的模型失败或影响0条, {} to {}", sourceModelName, targetModelName);
            }
        }
        return true;
    }

    @Override
    public int checkModelReference(String modelName) {
        int referenceCount = knowledgeBaseAppService.selectReferenceByModelName(modelName);
        referenceCount += searchConfigClient.selectReferenceByModelName(modelName);
        return referenceCount;
    }
}
