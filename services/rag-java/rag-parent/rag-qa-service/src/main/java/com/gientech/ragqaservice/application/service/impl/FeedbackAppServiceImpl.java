package com.gientech.ragqaservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.date.DateUtil;
import cn.hutool.core.util.ObjectUtil;
import com.alibaba.excel.support.ExcelTypeEnum;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.auth.dto.UserInfoDTO;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.qa.dto.FeedbackDTO;
import com.gientech.ragcommon.qa.dto.FeedbackExportDTO;
import com.gientech.ragcommon.qa.dto.HistoryDTO;
import com.gientech.ragcommon.qa.request.FeedbackQueryReq;
import com.gientech.ragcommon.qa.request.FeedbackReq;
import com.gientech.ragqaservice.application.helper.FeedbackExportHelper;
import com.gientech.ragqaservice.application.remote.UserInfoClient;
import com.gientech.ragqaservice.application.service.FeedbackAppService;
import com.gientech.ragqaservice.domain.entity.*;
import com.gientech.ragqaservice.domain.service.AnswerDomainService;
import com.gientech.ragqaservice.domain.service.FeedbackDomainService;
import com.gientech.ragqaservice.domain.service.QuestionDomainService;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.collections4.CollectionUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.*;

@Slf4j
@Service
public class FeedbackAppServiceImpl implements FeedbackAppService {

    @Autowired
    private FeedbackDomainService feedbackDomainService;

    @Autowired
    private AnswerDomainService answerDomainService;

    @Autowired
    private QuestionDomainService questionDomainService;

    @Autowired
    private UserInfoClient userInfoClient;

    @Value("${question.conf}")
    private String questionConf;

    @Autowired
    private FeedbackExportHelper feedbackExportHelper;

    @Override
    public Boolean feedback(FeedbackReq feedbackReq) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        String queryId = feedbackReq.getQueryId();
        Long answerId = answerDomainService.getAnswerIdByQueryId(queryId);
        Feedback dbFeedback = feedbackDomainService.findByAnswerIdAndUser(answerId, userName);
        if (Objects.isNull(dbFeedback)) {
            Feedback feedback = BeanUtil.copyProperties(feedbackReq, Feedback.class);
            feedback.setAnswerId(answerId);
            return feedbackDomainService.addFeedback(feedback);
        }
        Feedback updateFeedback = BeanUtil.copyProperties(feedbackReq, Feedback.class);
        updateFeedback.setAnswerId(answerId);
        updateFeedback.setId(dbFeedback.getId());
        return feedbackDomainService.updateById(updateFeedback);
    }

    @Override
    public Boolean cancel(String queryId) {
        Long answerId = answerDomainService.getAnswerIdByQueryId(queryId);
        return feedbackDomainService.deleteByAnswerId(answerId);
    }

    @Override
    public Page<FeedbackDTO> list(FeedbackQueryReq feedbackQueryReq) {
        Long pageNo = feedbackQueryReq.getPageNo();
        Long pageSize = feedbackQueryReq.getPageSize();
        Page<Feedback> feedbackPage = feedbackDomainService.list(
                feedbackQueryReq.getKeyList(),
                feedbackQueryReq.getStartTime(),
                feedbackQueryReq.getEndTime(),
                feedbackQueryReq.getFuzzy(),
                pageNo, pageSize);
        if(CollectionUtils.isEmpty(feedbackPage.getRecords()))
            return new Page<>();
        Page<FeedbackDTO> result = BeanUtil.copyProperties(feedbackPage, Page.class);
        result.setRecords(BeanUtil.copyToList(feedbackPage.getRecords(),FeedbackDTO.class));
        List<Long> listAnswerId = new ArrayList<>();
        for (FeedbackDTO oneFeedbackDTO : result.getRecords()) {
            listAnswerId.add(oneFeedbackDTO.getAnswerId());
        }

        List<ConfigNameAndAnswerId> configNameAndAnswerIdList = feedbackDomainService.inAnswerIdsBySearchConfigNames(listAnswerId);
        Map<Long,ConfigNameAndAnswerId> mapNames = new HashMap<>();
        for(ConfigNameAndAnswerId item:configNameAndAnswerIdList){
            mapNames.put(item.getAnswerId(),item);
        }
        //填充反馈的回答历史记录和助手名称
        for (FeedbackDTO oneFeedbackDTO : result.getRecords()) {
            ConfigNameAndAnswerId configNameAndAnswerId = mapNames.get(oneFeedbackDTO.getAnswerId());
            if(configNameAndAnswerId!=null){
                JSONObject jsonConfig = null;
                if(configNameAndAnswerId.getDialogueConfig()!=null){
                    jsonConfig = JSON.parseObject(configNameAndAnswerId.getDialogueConfig());
                }else if(configNameAndAnswerId.getConfigJson()!=null){
                    jsonConfig = JSON.parseObject(configNameAndAnswerId.getConfigJson());
                }
                String configName = null;
                Integer maxRound = 5;
                if(jsonConfig !=null ){
                     maxRound = jsonConfig.getInteger("max_round");
                    if(Objects.isNull(maxRound) || maxRound < 0 || maxRound >32){
                        maxRound = 5;
                    }
                    configName = jsonConfig.getString("name");
                    if(Objects.isNull(configName)){
                        configName = configNameAndAnswerId.getConfigName();
                    }
                }
                oneFeedbackDTO.setConfigName(configName);
                List<History> historyList = questionDomainService.getHistoryListByDialogueId(configNameAndAnswerId.getDialogueId(),configNameAndAnswerId.getAnswerId(),"gmtCreate", maxRound + 1);
                if(historyList!=null && historyList.size()>0){
                    if (historyList.size() > 1) {
                        List<History> histories = historyList.subList(1, historyList.size());
                        oneFeedbackDTO.setHistoryDTOList(BeanUtil.copyToList(histories, HistoryDTO.class));
                    }
                    History current = historyList.get(0);
                    oneFeedbackDTO.setAnwser(current.getAnswerContent());
                    oneFeedbackDTO.setQestion(current.getQueryContent());
                }
            }

            /**
             * 通过用户名获取用户信息
             */
            String userName = oneFeedbackDTO.getUserName();
            if(userName!=null&&!"".equals(userName)) {
                UserInfoDTO userInfo = userInfoClient.getUserInfoByUserName(userName);
                if(userInfo!=null){
                    oneFeedbackDTO.setUserPhone(userInfo.getUserPhone());
                    oneFeedbackDTO.setDeptName(userInfo.getDeptName());
                }
            }

        }
        return result;
    }

    @Override
    public List<JSONObject> queList() {
        return JSON.parseArray(questionConf, JSONObject.class);
    }


    @Override
    public void exportCsv(FeedbackQueryReq feedbackQueryReq, HttpServletResponse response) {
        String startTime = feedbackQueryReq.getStartTime();
        String endTime = feedbackQueryReq.getEndTime();
        String fuzzy = feedbackQueryReq.getFuzzy();
        List<FeedbackQueryReq.Key> keyList = feedbackQueryReq.getKeyList();
        Page<Feedback> feedbackPage = feedbackDomainService.list(keyList, startTime, endTime, fuzzy, 1L, 99999L);
        List<Feedback> dataList = feedbackPage.getRecords();
        try {
            if (ObjectUtil.isNotEmpty(dataList)) {
                List<Long> listAnswerId = new ArrayList<>();
                for (Feedback feedback : dataList) {
                    listAnswerId.add(feedback.getAnswerId());
                }
                List<ConfigNameAndAnswerId> configNameAndAnswerIdList = feedbackDomainService.inAnswerIdsBySearchConfigNames(listAnswerId);
                Map<Long,ConfigNameAndAnswerId> mapNames = new HashMap<>();
                for(ConfigNameAndAnswerId item:configNameAndAnswerIdList){
                    mapNames.put(item.getAnswerId(),item);
                }
                List<FeedbackExport> exportList = new ArrayList<>();
                for (Feedback feedback : dataList) {
                    FeedbackExport feedbackExport = BeanUtil.copyProperties(feedback, FeedbackExport.class);
                    ConfigNameAndAnswerId configNameAndAnswerId = mapNames.get(feedback.getAnswerId());
                    if(configNameAndAnswerId!=null){
                        JSONObject jsonConfig = null;
                        if(configNameAndAnswerId.getDialogueConfig()!=null){
                            jsonConfig = JSON.parseObject(configNameAndAnswerId.getDialogueConfig());
                        }else if(configNameAndAnswerId.getConfigJson()!=null){
                            jsonConfig = JSON.parseObject(configNameAndAnswerId.getConfigJson());
                        }
                        String configName = null;
                        Integer maxRound = 5;
                        if(jsonConfig !=null ){
                            maxRound = jsonConfig.getInteger("max_round");
                            if(Objects.isNull(maxRound) || maxRound < 0 || maxRound >32){
                                maxRound = 5;
                            }
                            configName = jsonConfig.getString("name");
                            if(Objects.isNull(configName)){
                                configName = configNameAndAnswerId.getConfigName();
                            }
                        }
                        StringBuffer sb = new StringBuffer();
                        if(feedback.getAnsPoor()!=null){
                            sb.append(feedback.getAnsPoor()+"。");
                        }
                        if(feedback.getFormatError()!=null){
                            sb.append(feedback.getFormatError()+"。");
                        }
                        if(feedback.getHarmfulInfo()!=null){
                            sb.append(feedback.getHarmfulInfo()+"。");
                        }
                        if(feedback.getOthres()!=null){
                            sb.append(feedback.getOthres()+"。");
                        }
                        feedbackExport.setIssueType(sb.toString());
                        feedbackExport.setConfigName(configName);
                        List<History> historyList = questionDomainService.getHistoryListByDialogueId(configNameAndAnswerId.getDialogueId(), configNameAndAnswerId.getAnswerId(),"gmtCreate", maxRound + 1);
                        if(CollectionUtils.isNotEmpty(historyList)){
                            StringBuffer sbCurrent = new StringBuffer();
                            History current = historyList.get(0);
                            sbCurrent.append("问题："+current.getQueryContent()).append(System.lineSeparator());
                            sbCurrent.append("答案："+current.getAnswerContent()).append(System.lineSeparator());
                            feedbackExport.setQuestionsAndAnswers(sbCurrent.toString());

                            if (historyList.size() > 1) {
                                List<History> histories = historyList.subList(1, historyList.size());
                                StringBuffer sbHistory = new StringBuffer();
                                for (History item : histories) {
                                    sbHistory.append("问题：" + item.getQueryContent()).append(System.lineSeparator());
                                    sbHistory.append("答案：" + item.getAnswerContent()).append(System.lineSeparator());
                                }
                                feedbackExport.setContext(sbHistory.toString());
                            }
                        }
                    }
                    exportList.add(feedbackExport);
                }
                feedbackExportHelper.exportData(
                "点踩收集_" + DateUtil.format(new Date(),"yyyyMMddHHmmss"),
                BeanUtil.copyToList(exportList, FeedbackExportDTO.class),
                        FeedbackExportDTO.class,
                ExcelTypeEnum.valueOf("xlsx".toUpperCase(Locale.ROOT)),
                response);
            }
        } catch (Exception e) {
            log.error("导出失败" + e.getMessage(), e);
        }
    }
}
