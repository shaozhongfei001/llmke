package com.gientech.ragindexservice.domain.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.alibaba.fastjson2.JSONObject;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.auth.dto.UserInfoDTO;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.dto.KnowledgeBaseDTO;
import com.gientech.ragcommon.index.enmus.DataBaseTypePrefixEnums;
import com.gientech.ragcommon.index.enmus.KbStatusEnums;
import com.gientech.ragcommon.index.enmus.ModelTypeEnums;
import com.gientech.ragcommon.index.enmus.PlatFormEnums;
import com.gientech.ragcommon.index.request.KnowledgeBaseCreateReq;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragindexservice.application.remote.UserClient;
import com.gientech.ragindexservice.application.service.ModelInfoAppService;
import com.gientech.ragindexservice.domain.entity.KnowledgeBase;
import com.gientech.ragindexservice.domain.repository.KnowledgeBaseRepository;
import com.gientech.ragindexservice.domain.service.KnowledgeBaseDomainService;
import com.gientech.ragindexservice.infrastructure.UrlKeywordChecker;
import com.gientech.start.storage.properties.Properties;
import com.gientech.start.storage.properties.StorageProperties;
import org.codehaus.plexus.util.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.util.*;

import static com.gientech.ragcommon.index.constant.KbConfigConstant.*;
import static com.gientech.ragcommon.index.constant.KbConfigConstant.GENERATE_GRAPH_MODEL_NAME;

/**
 * <p>
 * 知识库 服务实现类
 * </p>
 *
 * @author wudf
 * @since 2024-06-04
 */
@Service
public class KnowledgeBaseDomainServiceImpl implements KnowledgeBaseDomainService {

    @Autowired
    private KnowledgeBaseRepository knowledgeBaseRepository;

    @Autowired
    private UserClient userClient;

    @Autowired
    private ModelInfoAppService modelInfoAppService;

    @Autowired
    private StorageProperties storageProperties;

    @Override
    public KnowledgeBase addKnowledgeBase(KnowledgeBase knowledgeBase) {
        knowledgeBaseRepository.addKnowledgeBase(knowledgeBase);
        return knowledgeBase;
//        return knowledgeBaseRepository.findById(id);
    }

    @Override
    public KnowledgeBase findByKbName(String kbName, String userName) {
        KnowledgeBase knowledgeBase = knowledgeBaseRepository.findByKbName(kbName, userName);
        return Objects.isNull(knowledgeBase) ? null : knowledgeBase;
    }

    @Override
    public KnowledgeBase findByKbName(String kbName, String userName, String platform) {
        KnowledgeBase knowledgeBase = knowledgeBaseRepository.findByKbName(kbName, userName, platform);
        return Objects.isNull(knowledgeBase) ? null : knowledgeBase;
    }

    @Override
    public KnowledgeBase findByPrimitiveName(String primitiveName, String userName) {
        KnowledgeBase knowledgeBase = knowledgeBaseRepository.findByPrimitiveName(primitiveName, userName);
        return Objects.isNull(knowledgeBase) ? null : knowledgeBase;
    }

    @Override
    public List<KnowledgeBase> findByPrimitiveNames(List<String> primitiveNames) {
        List<KnowledgeBase> knowledgeBases = knowledgeBaseRepository.findByPrimitiveNames(primitiveNames);
        return CollectionUtils.isEmpty(knowledgeBases) ? null : knowledgeBases;
    }

    @Override
    public KnowledgeBase findByPrimitiveName(String primitiveName, String userName, String platform) {
        KnowledgeBase knowledgeBase = knowledgeBaseRepository.findByPrimitiveName(primitiveName, userName, platform);
        return Objects.isNull(knowledgeBase) ? null : knowledgeBase;
    }

    @Override
    public int deleteById(Long id) {
        KnowledgeBase knowledgeBase = new KnowledgeBase();
        knowledgeBase.setId(id);
        knowledgeBase.setStatus(KbStatusEnums.DELETE.getValue());
        return knowledgeBaseRepository.updateById(knowledgeBase);
    }

    @Override
    public Page<KnowledgeBase> list(List<Long> kbIds, String fuzzy, Long pageNo, Long pageSize, String userName, String platform, boolean isSuperAdmin, Integer privateKb) {
        return knowledgeBaseRepository.list(kbIds, fuzzy, pageNo, pageSize, userName, platform, isSuperAdmin, privateKb);
    }

    @Override
    public Page<KnowledgeBase> availableList(List<Long> kbIds, Long pageNo, Long pageSize) {
        return knowledgeBaseRepository.availableList(kbIds, pageNo, pageSize);
    }

    @Override
    public int updateById(KnowledgeBase knowledgeBase) {
        return knowledgeBaseRepository.updateById(knowledgeBase);
    }

    @Override
    public KnowledgeBase findByKbId(Long kbId) {
        KnowledgeBase knowledgeBase = knowledgeBaseRepository.findById(kbId);
        return Objects.isNull(knowledgeBase) ? null : knowledgeBase;
    }

    @Override
    public Integer getHighestPermission(Long kbId) {
        UserInfoDTO userInfoDTO = userClient.getUserInfo();
        return knowledgeBaseRepository.getHighestPermission(kbId, userInfoDTO.getLongTypeDeptId(), userInfoDTO.getId(), userInfoDTO.getUserName());
    }

    @Override
    public String queryCreator(Long id) {
        KnowledgeBase knowledgeBase = knowledgeBaseRepository.findById(id);
        return Objects.isNull(knowledgeBase) ? null : knowledgeBase.getCreateBy();
    }

    @Override
    public Boolean transferProperty(String owner, String receiver) {
        return knowledgeBaseRepository.transferProperty(owner, receiver) > 0;
    }

    @Override
    public KnowledgeBaseDTO createKb(KnowledgeBaseCreateReq kbReq) {
        String multiModelName = kbReq.getMultiModelName();
        String kbName = kbReq.getKbName().trim().replace(" ", "");
        if (StringUtils.isBlank(kbName))
            throw new ApplicationException(ErrCodeEnum.KB_NAME_EMPTY_ERROR);

        if (UrlKeywordChecker.containsUrlKeywords(kbName))
            throw new ApplicationException(ErrCodeEnum.KB_NAME_ILLEGAL);

        kbReq.setKbName(kbName);
        //重命名校验逻辑：当前用户纬度不能有重名知识库
        if (!Objects.isNull(this.findByKbName(kbName, UserContext.getUser().getUserName(), kbReq.getPlatform()))) {
            throw new ApplicationException(ErrCodeEnum.KB_NAME_SAME_ERROR);
        }

        //查询模型
        //嵌入模型
        String embeddingModelName = modelInfoAppService.getModelByType(ModelTypeEnums.EMBEDDING.getCode()).getModelName();
        //大模型
        String llmModelName = modelInfoAppService.getModelByType(ModelTypeEnums.LLM.getCode()).getModelName();
        //多模态模型
        if(StringUtils.isEmpty(multiModelName))
            multiModelName = modelInfoAppService.getModelByType(ModelTypeEnums.MULTI_MODEL.getCode()).getModelName();

        KnowledgeBase knowledgeBase = BeanUtil.copyProperties(kbReq, KnowledgeBase.class);
        knowledgeBase.setPrimitiveName(kbName);
        knowledgeBase.setSourceUrl(getSourceUrl(kbReq.getPlatform(), kbName));

        Map<String, Object> confMap = new HashMap<>();
        confMap.put(CHUNK_SIZE, kbReq.getChunkSize());
        confMap.put(SPLIT_REGEX, kbReq.getSplitRegex());
        confMap.put(CHUNK_OVERLAP, kbReq.getChunkOverlap());
        confMap.put(FILE_TYPE, kbReq.getFileType());
        confMap.put(EMBEDDING_MODEL_NAME,embeddingModelName);
        confMap.put(MODEL_NAME, llmModelName);
        confMap.put(MULTI_MODEL_NAME, multiModelName);

        //0代表不限
        confMap.put(FILE_FAQ_MAX_NUMS, 0);
        confMap.put(SIMILAR_QUESTION_MAX_NUMS, 1);
        confMap.put(FAQ_MODEL_NAME, llmModelName);

        //生成图谱的提示词
        confMap.put(GRAPH_PROMPT, kbReq.getGraphPrompt());
        confMap.put(GENERATE_GRAPH_MODEL_NAME, llmModelName);
        knowledgeBase.setConfig(JSONObject.toJSONString(confMap));
        knowledgeBase = this.addKnowledgeBase(knowledgeBase);

        //解决知识库重命名Bug问题
        knowledgeBase.setPrimitiveName(DataBaseTypePrefixEnums.KNOWLEDGE_BASE.getValue() + knowledgeBase.getId());
        knowledgeBase.setSourceUrl(getSourceUrl(kbReq.getPlatform(), knowledgeBase.getPrimitiveName()));
        this.updateById(knowledgeBase);
        return BeanUtil.copyProperties(knowledgeBase, KnowledgeBaseDTO.class);
    }

    private String getSourceUrl(String platform, String kbName) {
        Properties defaultStorageProperties = storageProperties.getDefaultStorageProperties();
        if (platform.equals(PlatFormEnums.RAG_QA.getCode())) {
            return String.format("%s/%s/%s/", defaultStorageProperties.getEndPoint(), defaultStorageProperties.getBucketName(), kbName);
        } else {
            return String.format("%s/%s/%s/%s/%s/", defaultStorageProperties.getEndPoint(), defaultStorageProperties.getBucketName(), platform, UserContext.getUser().getUserId(), kbName);
        }
    }

    @Override
    public Boolean replaceModel(String sourceModelName, String targetModelName) {
        return knowledgeBaseRepository.replaceModel(sourceModelName, targetModelName) > 0;
    }

    @Override
    public List<KnowledgeBase> selectUseSpecifiedModelKbList(String modelTypeName, String modelName){
        return knowledgeBaseRepository.selectUseSpecifiedModelKbList(modelTypeName, modelName);
    }

    @Override
    public int selectReferenceByModelName(String modelName) {
        return knowledgeBaseRepository.selectReferenceByModelName(modelName);
    }
}
