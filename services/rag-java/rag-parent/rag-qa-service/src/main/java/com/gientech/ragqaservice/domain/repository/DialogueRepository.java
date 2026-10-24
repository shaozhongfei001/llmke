package com.gientech.ragqaservice.domain.repository;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.infrastructure.exception.DomainException;
import com.gientech.ragcommon.qa.enmus.StatusEnums;
import com.gientech.ragcommon.qa.enmus.SysTypeEnums;
import com.gientech.ragqaservice.domain.entity.DbId;
import com.gientech.ragqaservice.domain.entity.Dialogue;

import java.util.List;

public interface DialogueRepository {

    Long addDialogue(Dialogue dialogue);

    Dialogue getDialogueById(Long id);

    Boolean deleteDialogueById(Long id);

    Boolean updateDialogueById(Dialogue dialogue);

    Boolean updateById(Dialogue dialogue);

    Dialogue getDialogueBySessionId(String sessionId) throws DomainException;

    Dialogue getDialogueByLabel(String label);

    boolean reName(Dialogue dialogue);

    Boolean updateStatus(Long dialogId, StatusEnums status);

    Page<Dialogue> list(String label,  SysTypeEnums sysType, Long pageNo, Long pageSize);

    Boolean updateStatusBySessionId(String sessionId, int status);

    Page<Dialogue> findListByConfId(Long configId, SysTypeEnums sysTypeEnums, Long pageNo, Long pageSize);

    DbId getIdsBySessionIdAndQueryId(String sessionId, String queryId);
}
