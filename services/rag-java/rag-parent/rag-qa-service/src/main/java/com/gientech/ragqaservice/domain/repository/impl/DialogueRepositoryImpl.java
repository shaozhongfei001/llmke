package com.gientech.ragqaservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import com.alibaba.fastjson2.JSON;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.infrastructure.exception.DomainException;
import com.gientech.ragcommon.qa.enmus.DialogueStatusEnums;
import com.gientech.ragcommon.qa.enmus.StatusEnums;
import com.gientech.ragcommon.qa.enmus.SysTypeEnums;
import com.gientech.ragqaservice.domain.conventer.DialogueConvertor;
import com.gientech.ragqaservice.domain.entity.*;
import com.gientech.ragqaservice.domain.mapper.DialogueMapper;
import com.gientech.ragqaservice.domain.model.DbIdDO;
import com.gientech.ragqaservice.domain.model.DialogueDO;
import com.gientech.ragqaservice.domain.repository.DialogueRepository;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;

import java.util.Date;
import java.util.List;
import java.util.Objects;
import java.util.stream.Collectors;

@Repository
public class DialogueRepositoryImpl implements DialogueRepository {

    @Autowired
    private DialogueMapper dialogueMapper;

    @Override
    public Long addDialogue(Dialogue dialogue) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        dialogue.setCreateBy(userName);
        dialogue.setUpdateBy(userName);
        dialogue.setGmtCreate(new Date());
        dialogue.setGmtModified(new Date());
        if (dialogue.getLabel() != null && dialogue.getLabel().length() >= 128) {
            dialogue.setLabel(dialogue.getLabel().substring(0, 128));
        }

        DialogueDO dialogueDO = DialogueConvertor.INSTANCE.dialogueToDialogueDO(dialogue);
        dialogueDO.setConfig(Objects.nonNull(dialogue.getConfig()) ? JSON.toJSONString(dialogue.getConfig()) : null);
//        DialogueDO dialogueDO = BeanUtil.copyProperties(dialogue, DialogueDO.class, "config");
//        if(Objects.nonNull(dialogue.getSearchConfig())){
//            dialogueDO.setConfig(JSONObject.toJSONString(dialogue.getSearchConfig()));
//        }

        dialogueMapper.insert(dialogueDO);
        dialogue.setId(dialogue.getId());
        return dialogueDO.getId();
    }

    @Override
    public Dialogue getDialogueById(Long id) {
        DialogueDO dialogueDO = dialogueMapper.selectById(id);
        Dialogue dialogue = DialogueConvertor.INSTANCE.dialogueDOToDialogue(dialogueDO);
//        Dialogue dialogue = BeanUtil.copyProperties(dialogueDO, Dialogue.class, "config");
//        dialogue.setSearchConfig(JSONObject.parseObject(dialogueDO.getConfig(), SearchConfig.class));
        return dialogue;
    }

    @Override
    public Boolean deleteDialogueById(Long id) {
        DialogueDO dialogueDO = dialogueMapper.selectById(id);
        if (Objects.isNull(dialogueDO)) {
            return false;
        }
        dialogueDO.setGmtModified(new Date());
        dialogueDO.setStatus(StatusEnums.DELETE.getCode());
        return dialogueMapper.updateById(dialogueDO) > 0;
    }

    @Override
    public Boolean updateDialogueById(Dialogue dialogue) {
        Long id = dialogue.getId();
        if (id == null) {
            return false;
        }
        dialogue.setGmtModified(new Date());
        return dialogueMapper.updateById(DialogueConvertor.INSTANCE.dialogueToDialogueDO(dialogue)) > 0;
    }

    @Override
    public Boolean updateById(Dialogue dialogue) {
        LambdaUpdateWrapper<DialogueDO>
                lambdaUpdateWrapper = new LambdaUpdateWrapper<>();
        lambdaUpdateWrapper.eq(DialogueDO::getId, dialogue.getId());

        lambdaUpdateWrapper.set(DialogueDO::getConfig, Objects.isNull(dialogue.getConfig()) ? null : JSON.toJSONString(dialogue.getConfig()));
        lambdaUpdateWrapper.set(DialogueDO::getConfigId, dialogue.getConfigId());
        lambdaUpdateWrapper.set(DialogueDO::getGmtModified, new Date());
        if (Objects.nonNull(dialogue.getStatus()))
            lambdaUpdateWrapper.set(DialogueDO::getStatus, dialogue.getStatus());
        if (StringUtils.isNotBlank(dialogue.getConfigHistory()))
            lambdaUpdateWrapper.set(DialogueDO::getConfigHistory, dialogue.getConfigHistory());
        if (Objects.nonNull(dialogue.getSysType()))
            lambdaUpdateWrapper.set(DialogueDO::getSysType, dialogue.getSysType());
        return dialogueMapper.update(lambdaUpdateWrapper) > 0;

    }

    @Override
    public Dialogue getDialogueBySessionId(String sessionId) throws DomainException {
        QueryWrapper<DialogueDO> wrapper = new QueryWrapper<>();
        wrapper.lambda().eq(DialogueDO::getSessionId, sessionId).last("limit 1");
        DialogueDO dialogueDO = dialogueMapper.selectOne(wrapper);
        return DialogueConvertor.INSTANCE.dialogueDOToDialogue(dialogueDO);
//        if (dialogueDO != null) {
//            Dialogue dialogue = BeanUtil.copyProperties(dialogueDO, Dialogue.class, "config");
//            dialogue.setSearchConfig(JSONObject.parseObject(dialogueDO.getConfig(), SearchConfig.class));
//            return dialogue;
//        } else {
//            return null;
//        }
    }

    @Override
    public Dialogue getDialogueByLabel(String label) {
        QueryWrapper<DialogueDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("create_by", UserContext.getUser().getUserName())
                .eq("label", label)
                .eq("status", DialogueStatusEnums.NORMAL.getCode()).last("limit 1");
        DialogueDO dialogueDO = dialogueMapper.selectOne(queryWrapper);
        return DialogueConvertor.INSTANCE.dialogueDOToDialogue(dialogueDO);
//        if(Objects.isNull(dialogueDO)){
//            return null;
//        }
//        Dialogue dialogue = BeanUtil.copyProperties(dialogueDO, Dialogue.class, "config");
//        dialogue.setSearchConfig(JSONObject.parseObject(dialogueDO.getConfig(), SearchConfig.class));
//        return dialogue;
    }

    @Override
    public boolean reName(Dialogue dialogue) {
        DialogueDO dialogueDO = BeanUtil.copyProperties(dialogue, DialogueDO.class);
        QueryWrapper<DialogueDO> queryWrapper = new QueryWrapper<>();
        dialogueDO.setGmtModified(new Date());
        queryWrapper
                .eq("session_id", dialogue.getSessionId())
                .ne("status", DialogueStatusEnums.DELETE.getCode());
        return dialogueMapper.update(dialogueDO, queryWrapper) > 0;
    }

    @Override
    public Boolean updateStatus(Long dialogId, StatusEnums status) {
        DialogueDO dialogueDO = new DialogueDO();
        dialogueDO.setId(dialogId);
        dialogueDO.setStatus(status.getCode());
        return dialogueMapper.updateById(dialogueDO) > 0;
    }

    @Override
    public Page<Dialogue> list(String label, SysTypeEnums sysType, Long pageNo, Long pageSize) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        QueryWrapper<DialogueDO> queryWrapper = new QueryWrapper<>();

        queryWrapper.lambda()
                .eq(DialogueDO::getCreateBy, userName)
                .eq(DialogueDO::getSysType,sysType.getCode())
                .ne(DialogueDO::getStatus, DialogueStatusEnums.DELETE.getCode());
        if (StringUtils.isNotBlank(label)) {
            queryWrapper.lambda().like(DialogueDO::getLabel, label);
        }
        queryWrapper.lambda().orderByDesc(DialogueDO::getGmtModified);
        Page<DialogueDO> page = new Page<>(pageNo, pageSize);
        Page<DialogueDO> pageResult = dialogueMapper.selectPage(page, queryWrapper);
        return DialogueConvertor.INSTANCE.dialogDOPageToDialogPage(pageResult);
//        Page<Dialogue> dialogueListPage = new Page<>();
//        BeanUtil.copyProperties(pageResult,dialogueListPage);
//        return dialogueListPage;
    }

    @Override
    public Boolean updateStatusBySessionId(String sessionId, int status) {
        DialogueDO dialogueDO = new DialogueDO();
        dialogueDO.setStatus(status);
        QueryWrapper<DialogueDO> queryWrapper = new QueryWrapper<>();
        queryWrapper
                .eq("session_id", sessionId)
                .ne("status", DialogueStatusEnums.DELETE.getCode());
        return dialogueMapper.update(dialogueDO, queryWrapper) > 0;
    }

    @Override
    public Page<Dialogue> findListByConfId(Long configId, SysTypeEnums sysTypeEnums, Long pageNo, Long pageSize) {
        QueryWrapper<DialogueDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.lambda()
                .eq(DialogueDO::getSysType, sysTypeEnums.getCode())
                .eq(DialogueDO::getConfigId,configId)
                .ne(DialogueDO::getStatus, DialogueStatusEnums.DELETE.getCode());
        Page<DialogueDO> page = new Page<>(pageNo, pageSize);
        Page<DialogueDO> pageResult = dialogueMapper.selectPage(page, queryWrapper);
        return DialogueConvertor.INSTANCE.dialogDOPageToDialogPage(pageResult);
    }

    @Override
    public DbId getIdsBySessionIdAndQueryId(String sessionId, String queryId) {
        List<DbIdDO> list = dialogueMapper.getIdsBySessionIdAndQueryId(sessionId, queryId);
        return list.size() <= 0 ? null : BeanUtil.copyProperties(list.get(0), DbId.class);
    }
}
