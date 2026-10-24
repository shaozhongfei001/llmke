package com.gientech.ragindexservice.domain.service.impl;

import com.alibaba.fastjson2.JSONArray;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.alibaba.fastjson2.JSONObject;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragindexservice.domain.entity.SynLog;
import com.gientech.ragindexservice.domain.repository.SynLogRepository;
import com.gientech.ragindexservice.domain.service.SynLogDomainService;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Objects;

/**
 * <p>
 * 日志 服务实现类
 * </p>
 *
 * @author wudf
 * @since 2024-08-27
 */
@Slf4j
@Service
public class SynLogDomainServiceImpl implements SynLogDomainService {

    @Autowired
    private SynLogRepository synLogRepository;

    @Override
    public SynLog findById(Long kbId, Long fileId) {
        return synLogRepository.findById(kbId,fileId);
    }

    @Override
    public void saveOrUpdate(SynLog synLog) {
        Long id = synLog.getId();
        if(!Objects.isNull(id))
            synLogRepository.updateById(synLog);
        else
            synLogRepository.save(synLog);
    }

    @Override
    public  List<SynLog> findByFileIds(List<Long> fileIds) {
        return synLogRepository.findByFileIds(fileIds);
    }

    @Override
    public void saveLog(Long kbId, Long fileId, Integer logType, JSONObject respObj,String errorMsg) {
//        SynLog synLog = this.findById(kbId, fileId);
//        if (Objects.isNull(synLog))
        SynLog synLog = SynLog.builder()
                    .kbId(kbId)
                    .targetId(fileId)
                    .logType(logType)
                    .build();
        synLog.setErrorMessage("系统服务异常，请联系管理员。");
        if (!Objects.isNull(respObj)) {
            String code = respObj.getString("code");
            synLog.setErrorCode(code);
            synLog.setErrorDetail(JSONObject.toJSONString(respObj));
        } else if(StringUtils.isNotBlank(errorMsg)){
            synLog.setErrorCode(String.valueOf(-1));
            synLog.setErrorDetail(errorMsg);
        }else {
            synLog.setErrorCode(String.valueOf(-1));
            synLog.setErrorDetail("接口不可用");
        }
        this.saveOrUpdate(synLog);
    }

    @Override
    public void saveLog(Long kbId, Long fileId, Integer logType, JSONObject respObj, String errorMsg, String errorDetail) {
        SynLog synLog = SynLog.builder()
                .kbId(kbId)
                .targetId(fileId)
                .logType(logType).errorCode(String.valueOf(-1))
                .errorMessage(errorMsg)
                .errorDetail(errorDetail)
                .build();

        if (!Objects.isNull(respObj)) {
            synLog.setErrorDetail(JSONObject.toJSONString(respObj));
            try {
                JSONArray taskStatuses = respObj.getJSONArray("task_statuses");
                if (!Objects.isNull(taskStatuses) && taskStatuses.size() > 0) {
                    Object taskStatuse = taskStatuses.get(0);
                    if (!Objects.isNull(taskStatuse)) {
                        JSONObject taskStatuseJson = (JSONObject) taskStatuse;
                        String code = taskStatuseJson.getString("code");
                        synLog.setErrorCode(code);
                        ErrCodeEnum errCodeEnum = ErrCodeEnum.getFileParseError(code);
                        synLog.setErrorMessage(Objects.isNull(errCodeEnum) ? null : errCodeEnum.getErrMsg());
                    }
                }
            } catch (Exception e) {
                log.error(e.getMessage());
            }
        }
        this.saveOrUpdate(synLog);
    }

    @Override
    public Page<SynLog> page(Long pageNo, Long pageSize, Long fileId) {
        return synLogRepository.page( pageNo, pageSize,fileId);
    }

    @Override
    public SynLog findByFileId(Long fileId) {
        return synLogRepository.findByFileId(fileId);
    }
}
