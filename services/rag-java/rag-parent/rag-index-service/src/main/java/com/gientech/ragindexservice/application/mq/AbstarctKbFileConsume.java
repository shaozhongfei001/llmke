package com.gientech.ragindexservice.application.mq;

import com.alibaba.fastjson2.JSONObject;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.index.parameter.FileParseTaskInfo;
import com.gientech.ragindexservice.domain.entity.KnowledgeBase;
import com.gientech.ragindexservice.domain.entity.KnowledgeBaseList;
import com.gientech.ragindexservice.domain.service.KnowledgeBaseDomainService;
import com.gientech.ragindexservice.domain.service.KnowledgeBaseListDomainService;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.core.RocketMQListener;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.util.CollectionUtils;
import java.util.List;
import java.util.Objects;

@Slf4j
public abstract class AbstarctKbFileConsume implements RocketMQListener<FileParseTaskInfo> {

    @Autowired
    private KnowledgeBaseDomainService knowledgeBaseDomainService;

    @Autowired
    private KnowledgeBaseListDomainService knowledgeBaseFileDomainService;

    protected abstract void dealFile(FileParseTaskInfo taskInfo);

    @Override
    public void onMessage(FileParseTaskInfo task) {
        log.info("收到的消息:{}", JSONObject.toJSONString(task));
        List<FileParseTaskInfo.File> files = task.getFiles();
        if (CollectionUtils.isEmpty(files)) {
            log.error("文件解析消息体为空");
            return;
        }
        KnowledgeBaseList kbFile = knowledgeBaseFileDomainService.findById(files.get(0).getFileId());
        log.info("files.get(0).getFileId:{}", files.get(0).getFileId());
        if (Objects.isNull(kbFile)) {
            log.warn("文件已删除");
            return;
        }
        KnowledgeBase kb = knowledgeBaseDomainService.findByKbId(kbFile.getKbId());
        if (Objects.isNull(kb)) {
            log.warn("知识库已经被删除,无需解析");
            return;
        }
        User user = new User();
        user.setUserId(task.getUserId());
        user.setUserName(task.getUserName());
        user.setApiKey(task.getApiKey());
        UserContext.setUser(user);
        this.dealFile(task);
    }
}
