package com.gientech.ragindexservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollUtil;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.auth.dto.PrivilegeDTO;
import com.gientech.ragcommon.auth.enums.PrivilegeTypeEnums;
import com.gientech.ragcommon.auth.enums.RoleTypeEnums;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.dto.BizLabelDTO;
import com.gientech.ragcommon.index.dto.Collaborator;
import com.gientech.ragcommon.index.dto.KnowledgeBaseDTO;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import com.gientech.ragcommon.index.enmus.*;
import com.gientech.ragcommon.index.request.*;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragindexservice.application.mq.message.ReEmbeddingTaskInfo;
import com.gientech.ragindexservice.application.remote.PrivilegeClient;
import com.gientech.ragindexservice.application.remote.SearchConfigClient;
import com.gientech.ragindexservice.application.remote.UserClient;
import com.gientech.ragindexservice.application.service.BizLabelAppService;
import com.gientech.ragindexservice.application.service.KnowledgeBaseAppService;
import com.gientech.ragindexservice.application.service.KnowledgeBaseListAppService;
import com.gientech.ragindexservice.application.service.ModelInfoAppService;
import com.gientech.ragindexservice.domain.entity.FolderInfo;
import com.gientech.ragindexservice.domain.entity.KnowledgeBase;
import com.gientech.ragindexservice.domain.entity.KnowledgeBaseFile;
import com.gientech.ragindexservice.domain.entity.KnowledgeBaseList;
import com.gientech.ragindexservice.domain.model.ReEmbeddingTaskDO;
import com.gientech.ragindexservice.domain.service.*;
import com.gientech.ragindexservice.infrastructure.UrlKeywordChecker;
import com.gientech.start.storage.properties.StorageProperties;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.client.producer.DefaultMQProducer;
import org.apache.rocketmq.client.producer.SendCallback;
import org.apache.rocketmq.client.producer.SendResult;
import org.apache.rocketmq.common.message.Message;
import org.codehaus.plexus.util.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.CollectionUtils;

import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.*;
import java.util.function.Function;
import java.util.stream.Collectors;

import static com.gientech.ragcommon.index.enmus.ModelTypeEnums.EMBEDDING;

/**
 * <p>
 * 知识库 服务类
 * </p>
 *
 * @author wudf
 * @since 2024-06-04
 */
@Slf4j
@Service
@RefreshScope
public class KnowledgeBaseAppServiceImpl implements KnowledgeBaseAppService {

    @Autowired
    private KnowledgeBaseDomainService knowledgeBaseDomainService;

    @Autowired
    private KnowledgeBaseListDomainService knowledgeBaseListDomainService;

    @Autowired
    private StorageProperties storageProperties;

    @Autowired
    private UserClient userClient;

    @Autowired
    private PrivilegeClient privilegeClient;

    @Autowired
    private SearchConfigClient searchConfigClient;

    @Autowired
    private ChunnkDomainService chunnkDomainService;

    @Autowired
    private FolderInfoDomainService folderInfoDomainService;

    @Autowired
    private KnowledgeBaseListAppService knowledgeBaseListAppService;

    @Autowired
    private GraphDomainService graphDomainService;

    @Autowired
    private BizLabelAppService bizLabelAppService;

    @Autowired
    private ModelInfoAppService modelInfoAppService;
    @Autowired
    private KnowledgeBaseAppService knowledgeBaseAppService;

    @Autowired
    private DefaultMQProducer producer;

    @Autowired
    private ReEmbeddingTaskService reEmbeddingTaskService;

    @Override
    public KnowledgeBaseDTO createKb(KnowledgeBaseCreateReq kbReq) {
        return knowledgeBaseDomainService.createKb(kbReq);
    }

    @Override
    public Boolean deleteById(Long id) {
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(id);
        if (knowledgeBaseDomainService.deleteById(id) > 0 && !Objects.isNull(knowledgeBase)) {
            Integer kbType = knowledgeBase.getKbType();
            //正常的知识库需要删除算法端的相关数据,文档上传问答不需要删除,因为不需要文本分块
            if (KbTypeEnums.KB.getCode().equals(kbType)) {
                String primitiveName = knowledgeBase.getPrimitiveName();
                String kbName = knowledgeBase.getKbName();
                try {
                    //删除表
                    chunnkDomainService.deleteTable(primitiveName);
                    //删除faq_表
                    chunnkDomainService.deleteTable(FileFieldEnums.FAQ_TABLE_NAME_PREFIX + primitiveName);
                    //删除table_summary_(摘要表)
                    chunnkDomainService.deleteTable(FileFieldEnums.TABLE_SUMMARY_PREFIX + primitiveName);
                    //删除 table_chunks_(chunk数据)
                    chunnkDomainService.deleteTable(FileFieldEnums.TABLE_CHUNKS_PREFIX + primitiveName);
                    //删除图空间
                    graphDomainService.delGraphSpace(primitiveName, null);
                    //milvus中图实体表删除
                    graphDomainService.delGraphEntity(primitiveName, null, null);
                } catch (Exception e) {
                    log.error("删除图数据库失败:{}", e.getMessage());
                }
                //更新助手配置
                searchConfigClient.updateKnowledgeBase(primitiveName, kbName);
            }
            return true;
        }
        return false;
    }

    @Override
    public Page<KnowledgeBaseDTO> list(KnowledgeBaseQueryReq knowledgeBaseQueryReq) {
        return getKbList(knowledgeBaseQueryReq, null, Maps.newHashMap(), UserContext.getUser().getUserName());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public Boolean update(KnowledgeBaseUpdateReq knowledgeBaseUpdateReq) {
        Long kbId = knowledgeBaseUpdateReq.getId();
        String kbName = knowledgeBaseUpdateReq.getKbName().trim().replace(" ", "");
        if (UrlKeywordChecker.containsUrlKeywords(kbName))
            throw new ApplicationException(ErrCodeEnum.KB_NAME_ILLEGAL);
        KnowledgeBase dbKnowledgeBase = knowledgeBaseDomainService.findByKbName(kbName, null);
        if (Objects.nonNull(dbKnowledgeBase) && !dbKnowledgeBase.getId().equals(kbId)) {
            throw new ApplicationException(ErrCodeEnum.KB_NAME_SAME_ERROR);
        }
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        knowledgeBaseUpdateReq.setPlatform(knowledgeBase.getPlatform());
        searchConfigClient.updateKbSourceName(knowledgeBase.getKbName(), kbName);
        return knowledgeBaseDomainService.updateById(BeanUtil.copyProperties(knowledgeBaseUpdateReq, KnowledgeBase.class)) > 0;
    }

    @Override
    public KnowledgeBaseDTO getKbById(Long id) {
        KnowledgeBase byKbId = knowledgeBaseDomainService.findByKbId(id);
        if (RoleTypeEnums.SUPER_ADMIN.getCode().equals(userClient.getUserType())) {
            //如果是超级管理员，直接赋予数据的最高权限
            byKbId.setPermission(PermissionEnums.ALL.getCode());
        } else {
            //查询数据权限
            List<PrivilegeDTO> privilegeDTOList = privilegeClient.getAllPermission(PrivilegeTypeEnums.KNOWLEDGE_BASE.getCode(), null);
            Map<Long, PrivilegeDTO> permissionMap = privilegeDTOList.stream().collect(Collectors.toMap(PrivilegeDTO::getTargetId, Function.identity(), (v1, v2) -> v1));

            if (!CollectionUtils.isEmpty(permissionMap)) {
                PrivilegeDTO privilegeDTO = permissionMap.get(byKbId.getId());
                byKbId.setPermission(Objects.isNull(privilegeDTO) ? null : privilegeDTO.getPermission());
            }

            if (UserContext.getUser().getUserName().equals(byKbId.getCreateBy()))
                byKbId.setPermission(PermissionEnums.ALL.getCode());
        }

        KnowledgeBaseDTO knowledgeBaseDTO = BeanUtil.copyProperties(byKbId, KnowledgeBaseDTO.class);
//        String config = byKbId.getConfig();
//        if (StringUtils.isNotBlank(config)) {
//            JSONObject confJson = JSONObject.parseObject(config);
//            knowledgeBaseDTO.setChunkSize(confJson.getInteger("chunkSize"));
//            knowledgeBaseDTO.setEmbeddingModelName(confJson.getString("embeddingModelName"));
//            knowledgeBaseDTO.setFileType(confJson.getString("fileType"));
//            knowledgeBaseDTO.setFileFaqMaxNums(confJson.getInteger("fileFaqMaxNums"));
//            knowledgeBaseDTO.setSimilarQuestionMaxNums(confJson.getInteger("similarQuestionMaxNums"));
//        }

        Map<Long, KnowledgeBaseFile> fileInfoMap = knowledgeBaseListDomainService.findFileInfo(Collections.singletonList(id));
        KnowledgeBaseFile knowledgeBaseFile = fileInfoMap.get(id);
        knowledgeBaseDTO.setFileCount(Objects.isNull(knowledgeBaseFile) ? 0 : knowledgeBaseFile.getFileCount());
        knowledgeBaseDTO.setFileTotalSize(Objects.isNull(knowledgeBaseFile) ? 0d : knowledgeBaseFile.getFileTotalSize());

        return knowledgeBaseDTO;
    }

    @Override
    public Page<KnowledgeBaseDTO> shareList(KnowledgeBaseQueryReq knowledgeBaseQueryReq) {
        if (RoleTypeEnums.SUPER_ADMIN.getCode().equals(userClient.getUserType())) {
            User user = UserContext.getUser();
            user.setUserName(null);
            Page<KnowledgeBaseDTO> page = this.list(knowledgeBaseQueryReq);
            page.getRecords().forEach(knowledgeBaseDTO -> knowledgeBaseDTO.setPermission(PermissionEnums.ALL.getCode()));
            return page;
        }
        List<PrivilegeDTO> privilegeDTOList = privilegeClient.getAllPermission(PrivilegeTypeEnums.KNOWLEDGE_BASE.getCode(), null);
        if (CollUtil.isEmpty(privilegeDTOList))
            return new Page<>();

        Map<Long, PrivilegeDTO> permissionMap = privilegeDTOList.stream().collect(Collectors.toMap(PrivilegeDTO::getTargetId, Function.identity(), (v1, v2) -> v1));
        return getKbList(knowledgeBaseQueryReq, new ArrayList<>(permissionMap.keySet()), permissionMap, null);
    }

    private Page<KnowledgeBaseDTO> getKbList(KnowledgeBaseQueryReq knowledgeBaseQueryReq, List<Long> targetKbIds, Map<Long, PrivilegeDTO> permissionMap, String userName) {
        String fuzzy = knowledgeBaseQueryReq.getFuzzy();
        Long pageNo = knowledgeBaseQueryReq.getPageNo();
        Long pageSize = knowledgeBaseQueryReq.getPageSize();
        Integer privateKb = knowledgeBaseQueryReq.getPrivateKB();

        Page<KnowledgeBase> knowledgeBasePage = knowledgeBaseDomainService.list(targetKbIds, fuzzy, pageNo, pageSize, userName, knowledgeBaseQueryReq.getPlatform(), knowledgeBaseQueryReq.isSuperAdmin(), privateKb);
        Page<KnowledgeBaseDTO> result = new Page<>();
        BeanUtil.copyProperties(knowledgeBasePage, result);
        List<KnowledgeBaseDTO> knowledgeBaseDTOS = BeanUtil.copyToList(knowledgeBasePage.getRecords(), KnowledgeBaseDTO.class);
        List<Long> kbIds = knowledgeBaseDTOS.stream().map(KnowledgeBaseDTO::getId).collect(Collectors.toList());
        if (!CollectionUtils.isEmpty(kbIds)) {
            Map<Long, KnowledgeBaseFile> fileInfoMap = knowledgeBaseListDomainService.findFileInfo(kbIds);
            knowledgeBaseDTOS.forEach(knowledgeBaseDTO -> {
                KnowledgeBaseFile knowledgeBaseFile = fileInfoMap.get(knowledgeBaseDTO.getId());
                PrivilegeDTO privilegeDTO = permissionMap.get(knowledgeBaseDTO.getId());
                knowledgeBaseDTO.setFileCount(Objects.isNull(knowledgeBaseFile) || Objects.isNull(knowledgeBaseFile.getFileCount()) ? 0 : knowledgeBaseFile.getFileCount());
                knowledgeBaseDTO.setFileTotalSize(Objects.isNull(knowledgeBaseFile) || Objects.isNull(knowledgeBaseFile.getFileTotalSize()) ? 0d : knowledgeBaseFile.getFileTotalSize());
                if (Objects.nonNull(privilegeDTO)) {
                    knowledgeBaseDTO.setPermission(privilegeDTO.getPermission());
                }
                setLabel(knowledgeBaseDTO);
            });
        }
        result.setRecords(knowledgeBaseDTOS);
        return result;
    }

    private void setLabel(KnowledgeBaseDTO knowledgeBaseDTO) {
        String joinedResult = Optional.ofNullable(
                        bizLabelAppService.findByTargetIds(List.of(knowledgeBaseDTO.getId()))
                )
                .filter(list -> !list.isEmpty())
                .map(list -> list.stream()
                        .map(BizLabelDTO::getLabel)
                        .collect(Collectors.joining(",")))
                .orElse("");
        knowledgeBaseDTO.setLabel(joinedResult);
    }

    @Override
    public Set<KnowledgeBaseDTO> searchList(String fuzzy, String userName, String platform) {
        KnowledgeBaseQueryReq knowledgeBaseQueryReq = new KnowledgeBaseQueryReq();
        knowledgeBaseQueryReq.setPlatform(platform);
        knowledgeBaseQueryReq.setPageNo(1L);
        knowledgeBaseQueryReq.setPageSize(10000L);
        if (RoleTypeEnums.SUPER_ADMIN.getCode().equals(userClient.getUserType()) ||
                RoleTypeEnums.SUPER_ADMIN.getCode().equals(userClient.getUserTypeByUserName(userName))) {
            //超级管理员查询所有的知识库数据
            User user = UserContext.getUser();
            user.setUserName(null);
            Page<KnowledgeBaseDTO> page = this.list(knowledgeBaseQueryReq);
            List<KnowledgeBaseDTO> userKbList = CollectionUtils.isEmpty(page.getRecords()) ? Lists.newArrayList() : page.getRecords();
            userKbList.forEach(knowledgeBaseDTO -> knowledgeBaseDTO.setPermission(PermissionEnums.ALL.getCode()));
            return new HashSet<>(BeanUtil.copyToList(userKbList, KnowledgeBaseDTO.class));
        }
        //查询用户自己创建的知识库
        knowledgeBaseQueryReq.setFuzzy(fuzzy);
        Page<KnowledgeBaseDTO> userKbPage = getKbList(knowledgeBaseQueryReq, null, Maps.newHashMap(), userName);
        List<KnowledgeBaseDTO> userKbList = CollectionUtils.isEmpty(userKbPage.getRecords()) ? Lists.newArrayList() : userKbPage.getRecords();
        //查询共享数据的知识库
        List<PrivilegeDTO> privilegeDTOList = privilegeClient.getAllPermission(PrivilegeTypeEnums.KNOWLEDGE_BASE.getCode(), userName);
        Map<Long, PrivilegeDTO> permissionMap = privilegeDTOList.stream().collect(Collectors.toMap(PrivilegeDTO::getTargetId, Function.identity(), (v1, v2) -> v1));
        if (!CollectionUtils.isEmpty(permissionMap)) {
            Page<KnowledgeBaseDTO> shareKbPage = getKbList(knowledgeBaseQueryReq, new ArrayList<>(permissionMap.keySet()), permissionMap, null);
            List<KnowledgeBaseDTO> shareKbList = CollectionUtils.isEmpty(shareKbPage.getRecords()) ? Lists.newArrayList() : shareKbPage.getRecords();
            userKbList.addAll(shareKbList);
        }
        return new HashSet<>(BeanUtil.copyToList(userKbList, KnowledgeBaseDTO.class));
    }

    @Override
    public Set<KnowledgeBaseDTO> searchList(String fuzzy, String userName, String platform, String scope) {
        KnowledgeBaseQueryReq knowledgeBaseQueryReq = new KnowledgeBaseQueryReq();
        knowledgeBaseQueryReq.setPlatform(platform);
        knowledgeBaseQueryReq.setScope(scope);
        knowledgeBaseQueryReq.setPageNo(1L);
        knowledgeBaseQueryReq.setPageSize(10000L);
        knowledgeBaseQueryReq.setUserName(userName);
        if (platform.equals(PlatFormEnums.RAG_QA.getCode()) && RoleTypeEnums.SUPER_ADMIN.getCode().equals(userClient.getUserType())) {
            //超级管理员查询所有的知识库数据
            User user = UserContext.getUser();
            user.setUserName(null);
            Page<KnowledgeBaseDTO> page = this.list(knowledgeBaseQueryReq);
            List<KnowledgeBaseDTO> userKbList = CollectionUtils.isEmpty(page.getRecords()) ? Lists.newArrayList() : page.getRecords();
            userKbList.forEach(knowledgeBaseDTO -> knowledgeBaseDTO.setPermission(PermissionEnums.ALL.getCode()));
            return new HashSet<>(BeanUtil.copyToList(userKbList, KnowledgeBaseDTO.class));
        }
        List<KnowledgeBaseDTO> userKbList = Lists.newArrayList();
        knowledgeBaseQueryReq.setFuzzy(fuzzy);
        switch (Objects.requireNonNull(KnowledgeBaseScopeEnums.of(scope))) {
            case OWN:
                //查询用户自己创建的知识库
                return new HashSet<>(BeanUtil.copyToList(getOwnKBList(knowledgeBaseQueryReq), KnowledgeBaseDTO.class));
            case SHARE:
                //查询共享数据的知识库
                return new HashSet<>(BeanUtil.copyToList(getShareKBList(knowledgeBaseQueryReq), KnowledgeBaseDTO.class));
            case ALL:
                List<KnowledgeBaseDTO> kbList = getOwnKBList(knowledgeBaseQueryReq);
                kbList.addAll(getShareKBList(knowledgeBaseQueryReq));
                return new HashSet<>(BeanUtil.copyToList(kbList, KnowledgeBaseDTO.class));
            default:
                return new HashSet<>(BeanUtil.copyToList(userKbList, KnowledgeBaseDTO.class));
        }


    }

    private List<KnowledgeBaseDTO> getShareKBList(KnowledgeBaseQueryReq knowledgeBaseQueryReq) {
        List<PrivilegeDTO> privilegeDTOList = privilegeClient.getAllPermission(PrivilegeTypeEnums.KNOWLEDGE_BASE.getCode(), knowledgeBaseQueryReq.getUserName());
        Map<Long, PrivilegeDTO> permissionMap = privilegeDTOList.stream().collect(Collectors.toMap(PrivilegeDTO::getTargetId, Function.identity(), (v1, v2) -> v1));
        if (!CollectionUtils.isEmpty(permissionMap)) {
            Page<KnowledgeBaseDTO> shareKbPage = getKbList(knowledgeBaseQueryReq, new ArrayList<>(permissionMap.keySet()), permissionMap, null);
            return CollectionUtils.isEmpty(shareKbPage.getRecords()) ? Lists.newArrayList() : shareKbPage.getRecords();
        }
        return Lists.newArrayList();
    }

    private List<KnowledgeBaseDTO> getOwnKBList(KnowledgeBaseQueryReq knowledgeBaseQueryReq) {
        Page<KnowledgeBaseDTO> userKbPage = getKbList(knowledgeBaseQueryReq, null, Maps.newHashMap(), knowledgeBaseQueryReq.getUserName());
        return CollectionUtils.isEmpty(userKbPage.getRecords()) ? Lists.newArrayList() : userKbPage.getRecords();
    }

    @Override
    public Boolean updateConf(KbConfUpdateReq updateConf) {
        Long id = updateConf.getId();
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(id);
        if (Objects.isNull(knowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);

        String config = bulidConfig(knowledgeBase.getConfig(), updateConf);
        knowledgeBase.setConfig(config);
        checkEmbeddingModelChangeAndSendMsg(knowledgeBase);
        knowledgeBaseDomainService.updateById(knowledgeBase);
        return true;
    }

    private void checkEmbeddingModelChangeAndSendMsg(KnowledgeBase knowledgeBase) {
        KnowledgeBaseDTO originalKb = knowledgeBaseAppService.getKbById(knowledgeBase.getId());
        String originalEmbeddingName = originalKb.getEmbeddingModelName();
        if (!originalEmbeddingName.equals(knowledgeBase.getEmbeddingModelName())) {
            //向量模型变更
            ModelSimpDTO chosenEmbeddingModel = modelInfoAppService.getByModeName(knowledgeBase.getEmbeddingModelName());
            String uid = UUID.randomUUID().toString();
            ReEmbeddingTaskDO reEmbeddingTaskDO = ReEmbeddingTaskDO.buildReEmbeddingTask(uid, knowledgeBase.getId(), knowledgeBase.getPrimitiveName(), knowledgeBase.getEmbeddingModelName());
            reEmbeddingTaskService.save(reEmbeddingTaskDO);
            Message message = ReEmbeddingTaskInfo.buildReEmbeddingMessage(reEmbeddingTaskDO.getId(), knowledgeBase.getId(), knowledgeBase.getPrimitiveName(), chosenEmbeddingModel);
            try {
                producer.send(message);
            } catch (Exception e) {
                log.error(e.getMessage(), e);
                // 记录日志？
            }
        }
    }


    private String bulidConfig(String config, KbConfUpdateReq updateConf) {

        JSONObject configJson = new JSONObject();
        if (StringUtils.isNotEmpty(config))
            configJson = JSON.parseObject(config);
        Integer kbConfigType = updateConf.getKbConfigType();

        if (StringUtils.isNotEmpty(updateConf.getFileType()))
            configJson.put("fileType", updateConf.getFileType());
        if (!Objects.isNull(updateConf.getChunkSize()))
            configJson.put("chunkSize", updateConf.getChunkSize());
        if (!Objects.isNull(updateConf.getChunkOverlap()))
            configJson.put("chunkOverlap", updateConf.getChunkOverlap());
        if (StringUtils.isNotEmpty(updateConf.getSplitRegex()))
            configJson.put("splitRegex", updateConf.getSplitRegex());

        if (KbConfigTypeEnums.FILE_PARSE.getCode().equals(kbConfigType)) {
            if (StringUtils.isNotEmpty(updateConf.getEmbeddingModelName())) {
                ModelSimpDTO modelInfo = modelInfoAppService.getSimpByModeName(updateConf.getEmbeddingModelName());
                configJson.put("embeddingModelName", modelInfo.getModelName());
            }
            if (StringUtils.isNotEmpty(updateConf.getModelName())) {
                ModelSimpDTO modelInfo = modelInfoAppService.getSimpByModeName(updateConf.getModelName());
                configJson.put("modelName", modelInfo.getModelName());
            }
            if (StringUtils.isNotEmpty(updateConf.getMultiModelName())) {
                ModelSimpDTO modelInfo = modelInfoAppService.getSimpByModeName(updateConf.getMultiModelName());
                configJson.put("multiModelName", modelInfo.getModelName());
            }
        } else if (KbConfigTypeEnums.FAQ.getCode().equals(kbConfigType)) {
            if (StringUtils.isNotEmpty(updateConf.getFaqModelName())) {
                ModelSimpDTO modelInfo = modelInfoAppService.getSimpByModeName(updateConf.getFaqModelName());
                configJson.put("faqModelName", modelInfo.getModelName());
            }
        } else if (KbConfigTypeEnums.GRAPH.getCode().equals(kbConfigType)) {
            if (StringUtils.isNotEmpty(updateConf.getGenerateGraphModelName())) {
                ModelSimpDTO modelInfo = modelInfoAppService.getSimpByModeName(updateConf.getGenerateGraphModelName());
                configJson.put("generateGraphModelName", modelInfo.getModelName());
            }
        } else
            throw new ApplicationException(ErrCodeEnum.KB_CONFIG_TYPE_ILLEGAL);

        if (!Objects.isNull(updateConf.getFileFaqMaxNums()))
            configJson.put("fileFaqMaxNums", updateConf.getFileFaqMaxNums());
        if (!Objects.isNull(updateConf.getSimilarQuestionMaxNums()))
            configJson.put("similarQuestionMaxNums", updateConf.getSimilarQuestionMaxNums());
        if (!Objects.isNull(updateConf.getEnablePolish()))
            configJson.put("enablePolish", updateConf.getEnablePolish());
        if (StringUtils.isNotEmpty(updateConf.getGraphPrompt()))
            configJson.put("graphPrompt", updateConf.getGraphPrompt());

        if ("intelligent".equals(updateConf.getFileType())) {
            configJson.put("chunkOverlap", null);
            configJson.put("splitRegex", null);
        } else if ("naive".equals(updateConf.getFileType())) {
            Integer chunkOverlap = updateConf.getChunkOverlap();
            Integer chunkSize = updateConf.getChunkSize();
            if (chunkOverlap >= chunkSize)
                throw new ApplicationException(ErrCodeEnum.CONF_CHUNKOVERLAP_CHUNKSIZE);
        }

        return JSON.toJSONString(configJson);
    }

    @Override
    public Boolean canUpdateConf(Long kbId) {
        List<Integer> parseStatus = Lists.newArrayList(2, 3); //解析中&解析成功
        List<Integer> extractStatus = Lists.newArrayList(2, 3); //抽取中&抽取成功
        List<KnowledgeBaseList> knowledgeBaseLists = knowledgeBaseListDomainService.findFileByKbIdAndFileStatus(kbId, parseStatus, extractStatus);
        return CollectionUtils.isEmpty(knowledgeBaseLists);
    }

    @Override
    // @Transactional(propagation = Propagation.REQUIRES_NEW)
    public KnowledgeBaseDTO rebuildNew(Long id) {
        // 获取旧知识库信息，新建同名知识库
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(id);
        knowledgeBase.setId(null);
        knowledgeBase = knowledgeBaseDomainService.addKnowledgeBase(knowledgeBase);
        Long newKbId = knowledgeBase.getId();

        // 旧知识库删除
        knowledgeBaseDomainService.deleteById(id);

        // 获取旧知识库文件夹
        List<Long> kbIds = new ArrayList<>();
        kbIds.add(id);
        List<FolderInfo> folderInfos = folderInfoDomainService.leveList(kbIds);
        // 将文件夹迁移到新知识库
        for (FolderInfo folderInfo : folderInfos) {
            folderInfoDomainService.updateFolderInfoKbId(folderInfo, newKbId);
        }

        // 获取旧知识库文档解析
        List<KnowledgeBaseList> fileParseList = knowledgeBaseListDomainService.findFileByKbId(id, ParseTypeEnums.FILE_PARSE.getCode());
        if (!CollectionUtils.isEmpty(fileParseList)) {
            // 将文档解析迁移到新知识库
            for (KnowledgeBaseList fileParse : fileParseList) {
                fileParse.setKbId(newKbId);
                knowledgeBaseListDomainService.update(fileParse);
            }
            // 重新文档解析
            int fileParseCount = 0;
            for (KnowledgeBaseList fileParse : fileParseList) {
                FilesParseReq filesParseReq = new FilesParseReq();
                List<FilesParseReq.File> files = new ArrayList<>();
                FilesParseReq.File file = new FilesParseReq.File();
                file.setFilePath(fileParse.getFilePath().substring(
                        fileParse.getFilePath().indexOf(storageProperties.getDefaultStorageProperties().getBucketName())));
                file.setFileSize(fileParse.getFileSize() + "MB");
                file.setFileId(fileParse.getId());
                file.setParentFileName(fileParse.getParentFileName());
                files.add(file);
                filesParseReq.setFiles(files);
                filesParseReq.setFolderIds(new ArrayList<>());
                filesParseReq.setKnowledgeBaseName(knowledgeBase.getKbName());
                filesParseReq.setKnowledgeBaseId(newKbId);
                filesParseReq.setOverride(true);
                try {
                    knowledgeBaseListAppService.filesParseNew(filesParseReq);
                    fileParseCount++;
                    // 每提交10个文件等待5秒
                    if (fileParseCount % 10 == 0) {
                        Thread.sleep(5000);
                    }
                } catch (Exception ex) {
                    log.warn("提交文件解析失败 fileId:" + fileParse.getId(), ex);
                }
            }
        }

        // 获取旧知识库FAQ解析
        List<KnowledgeBaseList> faqParseList = knowledgeBaseListDomainService.findFileByKbId(id, ParseTypeEnums.FAQ_PARSE.getCode());
        if (!CollectionUtils.isEmpty(faqParseList)) {
            // 将FAQ解析迁移到新知识库
            for (KnowledgeBaseList faqParse : faqParseList) {
                faqParse.setKbId(newKbId);
                knowledgeBaseListDomainService.update(faqParse);
            }
            // 重新FAQ解析
            int faqParseCount = 0;
            for (KnowledgeBaseList faqParse : faqParseList) {
                FilesParseReq filesParseReq = new FilesParseReq();
                List<FilesParseReq.File> files = new ArrayList<>();
                FilesParseReq.File file = new FilesParseReq.File();
                file.setFilePath(faqParse.getFilePath().substring(
                        faqParse.getFilePath().indexOf(storageProperties.getDefaultStorageProperties().getBucketName())));
                file.setFileSize(faqParse.getFileSize() + "MB");
                file.setFileId(faqParse.getId());
                file.setParentFileName(faqParse.getParentFileName());
                files.add(file);
                filesParseReq.setFiles(files);
                filesParseReq.setFolderIds(new ArrayList<>());
                filesParseReq.setKnowledgeBaseName(knowledgeBase.getKbName());
                filesParseReq.setKnowledgeBaseId(newKbId);
                filesParseReq.setOverride(true);
                try {
                    knowledgeBaseListAppService.filesExtractFAQNew(filesParseReq);
                    faqParseCount++;
                    // 每提交10个文件等待5秒
                    if (faqParseCount % 10 == 0) {
                        Thread.sleep(5000);
                    }
                } catch (Exception ex) {
                    log.warn("提交FAQ解析失败 fileId:" + faqParse.getId(), ex);
                }
            }
        }

        return BeanUtil.copyProperties(knowledgeBase, KnowledgeBaseDTO.class);
    }

    @Override
    public Boolean reParse(Long id) {
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(id);

        // 获取知识库文档解析
        List<KnowledgeBaseList> fileParseList = knowledgeBaseListDomainService.findFileByKbId(id, ParseTypeEnums.FILE_PARSE.getCode());
        if (!CollectionUtils.isEmpty(fileParseList)) {
            // 重新文档解析
            int fileParseCount = 0;
            for (KnowledgeBaseList fileParse : fileParseList) {
                FilesParseReq filesParseReq = new FilesParseReq();
                List<FilesParseReq.File> files = new ArrayList<>();
                FilesParseReq.File file = new FilesParseReq.File();
                file.setFilePath(fileParse.getFilePath().substring(
                        fileParse.getFilePath().indexOf(storageProperties.getDefaultStorageProperties().getBucketName())));
                file.setFileSize(fileParse.getFileSize() + "MB");
                file.setFileId(fileParse.getId());
                file.setParentFileName(fileParse.getParentFileName());
                files.add(file);
                filesParseReq.setFiles(files);
                filesParseReq.setFolderIds(new ArrayList<>());
                filesParseReq.setKnowledgeBaseName(knowledgeBase.getKbName());
                filesParseReq.setKnowledgeBaseId(id);
                filesParseReq.setOverride(true);
                try {
                    knowledgeBaseListAppService.filesParseNew(filesParseReq);
                    fileParseCount++;
//                    // 每提交10个文件等待5秒
//                    if (fileParseCount % 10 == 0) {
//                        Thread.sleep(5000);
//                    }
                } catch (Exception ex) {
                    log.warn("提交文件解析失败 fileId:" + fileParse.getId(), ex);
                }
            }
        }

        // 获取知识库FAQ解析
        List<KnowledgeBaseList> faqParseList = knowledgeBaseListDomainService.findFileByKbId(id, ParseTypeEnums.FAQ_PARSE.getCode());
        if (!CollectionUtils.isEmpty(faqParseList)) {
            // 重新FAQ解析
            int faqParseCount = 0;
            for (KnowledgeBaseList faqParse : faqParseList) {
                FilesParseReq filesParseReq = new FilesParseReq();
                List<FilesParseReq.File> files = new ArrayList<>();
                FilesParseReq.File file = new FilesParseReq.File();
                file.setFilePath(faqParse.getFilePath().substring(
                        faqParse.getFilePath().indexOf(storageProperties.getDefaultStorageProperties().getBucketName())));
                file.setFileSize(faqParse.getFileSize() + "MB");
                file.setFileId(faqParse.getId());
                file.setParentFileName(faqParse.getParentFileName());
                files.add(file);
                filesParseReq.setFiles(files);
                filesParseReq.setFolderIds(new ArrayList<>());
                filesParseReq.setKnowledgeBaseName(knowledgeBase.getKbName());
                filesParseReq.setKnowledgeBaseId(id);
                filesParseReq.setOverride(true);
                try {
                    knowledgeBaseListAppService.filesExtractFAQNew(filesParseReq);
                    faqParseCount++;
//                    // 每提交10个文件等待5秒
//                    if (faqParseCount % 10 == 0) {
//                        Thread.sleep(5000);
//                    }
                } catch (Exception ex) {
                    log.warn("提交FAQ解析失败 fileId:" + faqParse.getId(), ex);
                }
            }
        }

        return true;
    }

    @Override
    public Boolean downloadKbFiles(Long id) {
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(id);

        List<KnowledgeBaseList> kbFiles = knowledgeBaseListDomainService.findFileByKbId(id);
        String destinationDirectory = "C:/" + knowledgeBase.getKbName();
        try {
            Path destinationPath = Paths.get(destinationDirectory);
            if (Files.notExists(destinationPath)) {
                Files.createDirectories(destinationPath);
            }
        } catch (Exception ex) {
            log.error(ex.getMessage(), ex);
            return false;
        }

        for (KnowledgeBaseList kbFile : kbFiles) {
            String fileURL = kbFile.getFilePath();
            String destinationFileName = kbFile.getFileName();
            try {
                URL url = new URL(fileURL);
                HttpURLConnection httpURLConnection = (HttpURLConnection) url.openConnection();
                int responseCode = httpURLConnection.getResponseCode();

                // 检查响应码是否为HTTP OK
                if (responseCode == HttpURLConnection.HTTP_OK) {
                    InputStream inputStream = httpURLConnection.getInputStream();
                    Path destinationPath = Paths.get(destinationDirectory, destinationFileName);
                    Files.copy(inputStream, destinationPath, StandardCopyOption.REPLACE_EXISTING);
                }

                httpURLConnection.disconnect();
            } catch (Exception ex) {
                log.error("下载文件" + kbFile.getFileName() + "失败: " + ex.getMessage(), ex);
            }
        }

        return true;
    }

//    @Override
//    public List<KbEmbeddingModelDTO> getEmbeddingModels() {
//        return kbConfig.getKbEmbeddingModels();
//    }
//
//    @Override
//    public List<KbParseTypeDTO> getParseTypes() {
//        return kbConfig.getKbParseTypes();
//    }

    @Override
    public KnowledgeBaseDTO getKbByPrimitiveName(String primitiveName) {
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByPrimitiveName(primitiveName, null);
        return Objects.isNull(knowledgeBase) ? null : BeanUtil.copyProperties(knowledgeBase, KnowledgeBaseDTO.class);
    }

    @Override
    public String queryCreator(Long id) {
        return knowledgeBaseDomainService.queryCreator(id);

    }

    @Override
    public List<Collaborator> getCollaborators(Long kbId) {

        return List.of();
    }

    @Override
    public Integer getKbHighestPermission(Long kbId) {
        return knowledgeBaseDomainService.getHighestPermission(kbId);
    }

    @Override
    public Boolean transferProperty(String owner, String receiver) {
        return knowledgeBaseDomainService.transferProperty(owner, receiver);
    }

    @Override
    public Boolean replaceModel(String taskUUID, String modelTypeName, String sourceModelName, String targetModelName) {
        sendReEmbeddingMessage(taskUUID, modelTypeName, sourceModelName, targetModelName);
        return knowledgeBaseDomainService.replaceModel(sourceModelName, targetModelName);
    }

    private void sendReEmbeddingMessage(String taskUUID, String modelTypeName, String sourceModelName, String targetModelName) {
        if (!modelTypeName.equals(EMBEDDING.getFieldName())) {
            return;
        }
        List<KnowledgeBase> knowledgeBases = knowledgeBaseDomainService.selectUseSpecifiedModelKbList(modelTypeName, sourceModelName);
        ModelSimpDTO reEmbeddingModel = modelInfoAppService.getSimpByModeName(targetModelName);
        if (!CollectionUtils.isEmpty(knowledgeBases)) {
            for (KnowledgeBase knowledgeBase : knowledgeBases) {
                ReEmbeddingTaskDO reEmbeddingTaskDO = ReEmbeddingTaskDO.buildReEmbeddingTask(taskUUID, knowledgeBase.getId(), knowledgeBase.getPrimitiveName(), targetModelName);
                reEmbeddingTaskService.save(reEmbeddingTaskDO);
                Message message = ReEmbeddingTaskInfo.buildReEmbeddingMessage(reEmbeddingTaskDO.getId(), knowledgeBase.getId(), knowledgeBase.getPrimitiveName(), reEmbeddingModel);
                try {
                    producer.send(message, new SendCallback() {
                        @Override
                        public void onSuccess(SendResult sendResult) {
                            System.out.println("异步发送成功: " + sendResult);
                        }

                        @Override
                        public void onException(Throwable e) {
                            System.err.println("异步发送失败: " + e.getMessage());
                        }
                    });
                } catch (Exception ex) {
                    log.error(ex.getMessage(), ex);
                }
            }
        }
    }

    @Override
    public List<KnowledgeBase> selectUseSpecifiedModelKbList(String modelTypeName, String modelName){
        return knowledgeBaseDomainService.selectUseSpecifiedModelKbList(modelTypeName, modelName);
    }

    @Override
    public int selectReferenceByModelName(String modelName) {
        return knowledgeBaseDomainService.selectReferenceByModelName(modelName);
    }
}

