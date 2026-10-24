package com.gientech.ragqaservice.domain.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.gientech.ragcommon.infrastructure.exception.DomainException;
import com.gientech.ragcommon.qa.enmus.StatusEnums;
import com.gientech.ragcommon.qa.enmus.SysTypeEnums;
import com.gientech.ragqaservice.domain.entity.DbId;
import com.gientech.ragqaservice.domain.entity.Dialogue;
import com.gientech.ragqaservice.domain.mapper.DialogueMapper;
import com.gientech.ragqaservice.domain.model.DialogueDO;
import com.gientech.ragqaservice.domain.repository.DialogueRepository;
import com.gientech.ragqaservice.domain.service.AnswerDomainService;
import com.gientech.ragqaservice.domain.service.DialogueDomainService;
import com.gientech.ragqaservice.domain.service.QuestionDomainService;
import org.springframework.stereotype.Service;

import java.util.Date;

/**
 * <p>
 * 对话表 服务实现类
 * </p>
 *
 * @author wudf
 * @since 2024-06-24
 */
@Service
public class DialogueDomainServiceImpl extends ServiceImpl<DialogueMapper, DialogueDO> implements DialogueDomainService {


    private final DialogueRepository dialogueRepository;

    private final QuestionDomainService questionDomainService;

    private final AnswerDomainService answerDomainService;

    public DialogueDomainServiceImpl(DialogueRepository dialogueRepository, QuestionDomainService questionDomainService, AnswerDomainService answerDomainService) {
        this.dialogueRepository = dialogueRepository;
        this.questionDomainService = questionDomainService;
        this.answerDomainService = answerDomainService;
    }

    @Override
    public Long addDialogue(Dialogue dialogue) throws DomainException {
        return dialogueRepository.addDialogue(dialogue);
    }

    @Override
    public Dialogue getDialogueById(Long id) throws DomainException {
        return dialogueRepository.getDialogueById(id);
    }

    @Override
    public Boolean deleteDialogueById(Long id) throws DomainException {
        return dialogueRepository.deleteDialogueById(id);
    }

    @Override
    public Boolean updateDialogueById(Dialogue dialogue) throws DomainException {
        return dialogueRepository.updateDialogueById(dialogue);
    }

    @Override
    public Long addAndGetIdBySessionId(String sessionId, SysTypeEnums sysTypeEnums) throws DomainException {
        Dialogue dialogue = dialogueRepository.getDialogueBySessionId(sessionId);
        if (dialogue == null) {
            dialogue = new Dialogue();
            dialogue.setSessionId(sessionId);
            dialogue.setStatus(1);
            dialogue.setSysType(sysTypeEnums.getCode());
            Long id = dialogueRepository.addDialogue(dialogue);
            dialogue.setId(id);
        } else {
            dialogue.setStatus(StatusEnums.ERROR.getCode());
            //dialogue.setSysType(sysTypeEnums.getCode());
            dialogueRepository.updateDialogueById(dialogue);
        }
        return dialogue.getId();
    }

    @Override
    public Long addOrUpdateBySessionId(Dialogue reqDialogue) {
        Dialogue dialogue = dialogueRepository.getDialogueBySessionId(reqDialogue.getSessionId());
        if (dialogue == null) {
            dialogue = BeanUtil.copyProperties(reqDialogue, Dialogue.class);
            dialogue.setStatus(StatusEnums.NORMAL.getCode());
            Long id = dialogueRepository.addDialogue(dialogue);
            dialogue.setId(id);
        } else {
            dialogue.setConfigId(reqDialogue.getConfigId());
            dialogue.setConfig(reqDialogue.getConfig());
            dialogue.setConfigHistory(reqDialogue.getConfigHistory());
            dialogue.setStatus(StatusEnums.ERROR.getCode());
            dialogue.setGmtModified(new Date());
            //dialogue.setSysType(sysTypeEnums.getCode());
            dialogueRepository.updateById(dialogue);
        }
        return dialogue.getId();
    }

    @Override
    public Dialogue getDialogueByLabel(String label) throws DomainException {
        return dialogueRepository.getDialogueByLabel(label);
    }

    @Override
    public boolean reName(Dialogue dialogue) {
        return dialogueRepository.reName(dialogue);
    }

    @Override
    public Boolean updateStatus(Long dialogId, StatusEnums status) {
        return dialogueRepository.updateStatus(dialogId, status);
    }

    @Override
    public Dialogue getDialogueBySessionId(String sessionId) {
        return dialogueRepository.getDialogueBySessionId(sessionId);
    }

    @Override
    public Boolean updateStatusBySessionId(String sessionId, int status) {
        return dialogueRepository.updateStatusBySessionId(sessionId, status);
    }

    @Override
    public Page<Dialogue> list(String label, SysTypeEnums sysType, Long pageNo, Long pageSize) {
        return dialogueRepository.list(label, sysType, pageNo, pageSize);
    }

    @Override
    public Page<Dialogue> findListByConfId(Long configId, SysTypeEnums sysTypeEnums, Long pageNo, Long pageSize) {
        return dialogueRepository.findListByConfId(configId, sysTypeEnums, pageNo, pageSize);
    }

    @Override
    public Boolean updateById(Dialogue dialogue) {
        return dialogueRepository.updateById(dialogue);
    }

    @Override
    public DbId getIdsBySessionIdAndQueryId(String sessionId, String queryId) {
        return dialogueRepository.getIdsBySessionIdAndQueryId(sessionId, queryId);
    }
}
