package com.gientech.ragqaservice.domain.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.infrastructure.exception.DomainException;
import com.gientech.ragcommon.qa.enmus.StatusEnums;
import com.gientech.ragcommon.qa.enmus.SysTypeEnums;
import com.gientech.ragqaservice.domain.entity.DbId;
import com.gientech.ragqaservice.domain.entity.Dialogue;
import com.gientech.ragqaservice.domain.model.DialogueDO;
import com.baomidou.mybatisplus.extension.service.IService;

import java.util.List;

/**
 * <p>
 * 对话表 服务类
 * </p>
 *
 * @author wudf
 * @since 2024-06-24
 */
public interface DialogueDomainService extends IService<DialogueDO> {

    Long addDialogue(Dialogue dialogue) throws DomainException;

    Dialogue getDialogueById(Long id) throws DomainException;

    Boolean deleteDialogueById(Long id) throws DomainException;

    Boolean updateDialogueById(Dialogue dialogue) throws DomainException;

    Long addAndGetIdBySessionId(String sessionId, SysTypeEnums sysTypeEnums) throws DomainException;

    Long addOrUpdateBySessionId(Dialogue dialogue) ;

    Dialogue getDialogueByLabel(String label) throws DomainException;

    boolean reName(Dialogue dialogue);

    Boolean updateStatus(Long dialogId, StatusEnums status);

    Dialogue getDialogueBySessionId(String sessionId);

    Boolean updateStatusBySessionId(String sessionId, int status);

    Page<Dialogue> list(String label, SysTypeEnums sysType, Long pageNo, Long pageSize);

    Page<Dialogue> findListByConfId(Long configId, SysTypeEnums sysTypeEnums, Long pageNo, Long pageSize);

    Boolean updateById(Dialogue dialogue);

    DbId getIdsBySessionIdAndQueryId(String sessionId, String queryId);
}
