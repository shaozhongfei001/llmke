package com.gientech.ragqaservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.alibaba.fastjson2.JSON;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.auth.enums.PrivilegeTypeEnums;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.dto.KnowledgeBaseDTO;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragcommon.qa.dto.AnswerDTO;
import com.gientech.ragcommon.qa.dto.DialogDTO;
import com.gientech.ragcommon.qa.dto.QueryReplyPairDTO;
import com.gientech.ragcommon.qa.dto.QuestionDTO;
import com.gientech.ragcommon.qa.enmus.AIResultTypeEnum;
import com.gientech.ragcommon.qa.enmus.DialogueStatusEnums;
import com.gientech.ragcommon.qa.entity.Config;
import com.gientech.ragcommon.qa.request.DialogCreateRequest;
import com.gientech.ragcommon.qa.request.DialogQueryRequest;
import com.gientech.ragcommon.qa.request.DialogRenameRequest;
import com.gientech.ragqaservice.application.remote.AuthClient;
import com.gientech.ragqaservice.application.remote.KbClient;
import com.gientech.ragqaservice.application.service.DialogueAppService;
import com.gientech.ragqaservice.domain.conventer.DialogueConvertor;
import com.gientech.ragqaservice.domain.conventer.SearchConfigConvertor;
import com.gientech.ragqaservice.domain.entity.*;
import com.gientech.ragqaservice.domain.model.AnswerDO;
import com.gientech.ragqaservice.domain.service.*;
import com.gientech.ragqaservice.infrastructure.NacosConfig;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.*;

@Slf4j
@Service
public class DialogueAppServiceImpl implements DialogueAppService {

    @Autowired
    private DialogueDomainService dialogueDomainService;

    @Autowired
    private QuestionDomainService questionDomainService;

    @Autowired
    private AnswerDomainService answerDomainService;

    @Autowired
    public NacosConfig nacosConfig;

    @Autowired
    private FeedbackDomainService feedbackDomainService;

    @Autowired
    private SearchConfigDomainService searchConfigDomainService;

    @Autowired
    private AuthClient authClient;

    @Autowired
    private KbClient kbClient;

    @Autowired
    private ApiKeyInfoDomainService apiKeyInfoDomainService;

    @Override
    public DialogDTO create(DialogCreateRequest createRequest) {
        Dialogue dialogue = BeanUtil.copyProperties(createRequest, Dialogue.class, "configId");
        Long configId = createRequest.getConfigId();
        Long kbId = createRequest.getKbId();
        //创建对话时，将当前助手配置信息持久化到对话里
        if (Objects.nonNull(configId) && configId > 0) {
            //判断是否有检索配置的数据权限
            Boolean permission = false;
            String apiKey = UserContext.getUser().getApiKey();
            if (StringUtils.isNotBlank(apiKey) && !apiKeyInfoDomainService.checkApiKey(apiKey)) {
                //apikey方式调用，需要校验apiKye的合法性
                log.error("apiKey:【{}】不合法", apiKey);
                throw new ApplicationException(ErrCodeEnum.API_KEY_NOT_LEGAL);
            } else if (StringUtils.isEmpty(apiKey)) {
                //正常用户使用
                Config searchConfig = searchConfigDomainService.getConfigById(configId);
                //自己创建的检索配置有权限
                permission = Objects.nonNull(searchConfig) && searchConfig.getCreateBy().equals(UserContext.getUser().getUserName());
                //判断是否有数据权限
                if (!permission && Objects.nonNull(searchConfig)) {
                    permission = authClient.isPermission(PrivilegeTypeEnums.INDEX_CONF.getCode(), configId);
                }
                if (permission) {
                    dialogue.setConfigId(configId);
                    dialogue.setConfig(searchConfig);
                    dialogue.setConfigHistory(JSON.toJSONString(Arrays.asList(searchConfig)));
                }
            }
        }

        dialogueDomainService.addDialogue(dialogue);
        return DialogueConvertor.INSTANCE.dialogueToDialogDTO(dialogue);
//        return BeanUtil.copyProperties(dialogue, DialogDTO.class);
    }

    @Override
    public DialogDTO reName(DialogRenameRequest renameRequest) {
        String sessionId = renameRequest.getSessionId();
        Dialogue dialogue = dialogueDomainService.getDialogueBySessionId(sessionId);
        if (StringUtils.isNotBlank(dialogue.getLabel()) && dialogue.getLabel().equals(renameRequest.getLabel()))
            throw new ApplicationException(ErrCodeEnum.DIALOG_NAME_SAME_ERROR);
        if (!dialogueDomainService.reName(BeanUtil.copyProperties(renameRequest, Dialogue.class)))
            throw new ApplicationException(ErrCodeEnum.DIALOG_RENAME_FAIL_ERROR);
        dialogue.setLabel(renameRequest.getLabel());
        return DialogueConvertor.INSTANCE.dialogueToDialogDTO(dialogue);
//        return BeanUtil.copyProperties(dialogue, DialogDTO.class);
    }

    @Override
    public Boolean delete(String sessionId) {
        dialogueDomainService.updateStatusBySessionId(sessionId, DialogueStatusEnums.DELETE.getCode());
        //删除当前对话中的知识库数据
        KnowledgeBaseDTO kb = kbClient.getKbByPrimitiveName(sessionId);
        if (!Objects.isNull(kb))
            kbClient.deleteById(kb.getId());
        return true;
    }

    @Override
    public DialogDTO getDialogBySessionId(String sessionId) {
        Dialogue dialogue = dialogueDomainService.getDialogueBySessionId(sessionId);
        if (dialogue != null) {
            List<Question> questionList = questionDomainService.getQuestionListByDialogueId(dialogue.getId());
            Map<Long, Answer> answerMap = Maps.newHashMap();
            Map<Long, Feedback> feedMap = Maps.newHashMap();
            answerToMap(answerMap, feedMap, dialogue.getId());
            List<QueryReplyPairDTO> queryReplyPairList = new ArrayList<>();
            for (Question item : questionList) {
                QueryReplyPairDTO queryReplyPairDTO = new QueryReplyPairDTO();
                QuestionDTO questionDTO = BeanUtil.copyProperties(item, QuestionDTO.class);
                questionDTO.setQueryId(item.getFrontUuid());
                questionDTO.setCurrentFiles(item.getAlgParams());
                queryReplyPairDTO.setQuery(questionDTO);
                Answer answer = answerMap.get(item.getId());
                if (answer != null) {
                    AnswerDTO answerDTO = BeanUtil.copyProperties(answer, AnswerDTO.class);
                    answerDTO.setQueryId(item.getFrontUuid());
                    Feedback feedback = feedMap.get(answer.getId());
                    answerDTO.setFeedbackResult(Objects.isNull(feedback) ? null : feedback.getRestult());
                    answerDTO.setFeedbackId(Objects.isNull(feedback) ? null : feedback.getId());
                    Integer resultType = answerDTO.getResultType();
                    queryReplyPairDTO.setReply(answerDTO);
                    String reference = answerDTO.getReference();
                    questionDTO.setFilePaths(AIResultTypeEnum.FILE_UPLOAD.getCode().equals(resultType) ? reference : null);
                    answerDTO.setReference(answer.getReference());
                }
                queryReplyPairList.add(queryReplyPairDTO);
            }
            DialogDTO dialogDTO = DialogueConvertor.INSTANCE.dialogueToDialogDTO(dialogue);
//            DialogDTO dialogDTO = BeanUtil.copyProperties(dialogue, DialogDTO.class);
            dialogDTO.setQueryReplyPairList(queryReplyPairList);
            dialogDTO.setFilePath(nacosConfig.getMinioUrl());
            Config config = dialogue.getConfig();
            if (Objects.isNull(config)) {
                config = searchConfigDomainService.getDefaultConfig();
            }
            dialogue.setConfig(config);
            dialogDTO.setSearchConfigDTO(SearchConfigConvertor.INSTANCE.searchConfigToSearchConfigDto(config));
            return dialogDTO;
        }
        return null;
    }

    private void answerToMap(Map<Long, Answer> answerMap, Map<Long, Feedback> feedMap, Long dialogueId) {
        List<Answer> answerList = answerDomainService.getAnswerListByDialogueId(dialogueId);
        List<Long> answerIds = Lists.newArrayList();
        answerList.forEach(answer -> {
            answerMap.put(answer.getQuestionId(), answer);
            answerIds.add(answer.getId());
        });
        feedbackDomainService.findByIds(answerIds).forEach(feedback -> feedMap.put(feedback.getAnswerId(), feedback));
    }

    @Override
    public Page<DialogDTO> list(DialogQueryRequest queryRequest) {
        Page<Dialogue> dialoguePage = dialogueDomainService.list(queryRequest.getLabel(), queryRequest.getSysType(), queryRequest.getPageNo(), queryRequest.getPageSize());
        return DialogueConvertor.INSTANCE.dialogPageToDialogDTOPage(dialoguePage);

//        Page<DialogDTO> result = new Page<>();
//        result.setRecords(BeanUtil.copyToList(dialoguePage.getRecords(), DialogDTO.class));
//        return result;
    }

    @Override
    public Boolean updateQaFiles(String queryId, String filePaths) {
        Answer answer = answerDomainService.getAnswerByQueryId(queryId);
        if (Objects.isNull(answer) || StringUtils.isEmpty(filePaths))
            return false;
        answer.setReference(filePaths);
        return answerDomainService.updateById(BeanUtil.copyProperties(answer, AnswerDO.class));
    }


}
