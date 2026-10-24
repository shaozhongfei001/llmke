package com.gientech.ragauthservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.util.IdUtil;
import com.gientech.ragauthservice.application.service.KaptchaAppService;
import com.gientech.ragauthservice.application.service.UserInfoAppService;
import com.gientech.ragauthservice.application.service.UserSecurityQuestionAppService;
import com.gientech.ragauthservice.domain.entity.UserSecurityQuestion;
import com.gientech.ragauthservice.domain.service.UserSecurityQuestionDomainService;
import com.gientech.ragcommon.auth.dto.UserSecurityQuestionDTO;
import com.gientech.ragauthservice.interfaces.req.UpdatePasswordByQuestionReq;
import com.gientech.ragauthservice.interfaces.req.ValidateSecurityQuestionReq;
import com.gientech.ragcommon.auth.dto.UserInfoDTO;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.start.redisson.utils.RedissonUtils;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.Maps;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Lazy;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Objects;
import java.util.concurrent.TimeUnit;

@Service
public class UserSecurityQuestionAppServiceImpl implements UserSecurityQuestionAppService {

    @Autowired
    private UserSecurityQuestionDomainService userSecurityQuestionDomainService;

    @Lazy
    @Autowired
    private UserInfoAppService userInfoAppService;

    @Autowired
    private RedissonUtils redissonUtils;

    @Autowired
    private KaptchaAppService kaptchaAppService;

    private final long VALIDATE_EXPIRED = 60 * 15;

    private final String VALIDATE_SUFFIX = "security:question:validate:";

    @Override
    public Boolean isSetSecurityQuestion(Long userId) {
        Long count = userSecurityQuestionDomainService.countByUserId(userId);
        return count>0?true:false;
    }

    @Override
    public List<UserSecurityQuestionDTO> findByUserId(Long userId, Boolean hideAnswer) {
        List<UserSecurityQuestion> userSecurityQuestions = userSecurityQuestionDomainService.findByUserId(userId);
        if(hideAnswer){
            for(UserSecurityQuestion userSecurityQuestion:userSecurityQuestions){
                userSecurityQuestion.setAnswer(null);
            }
        }
        return BeanUtil.copyToList(userSecurityQuestions,UserSecurityQuestionDTO.class);
    }

    @Override
    public List<UserSecurityQuestionDTO> findByUserName(String userName, Boolean hideAnswer) {
        UserInfoDTO userInfoDTO = userInfoAppService.getUserInfoByUserName(userName);
        if(userInfoDTO==null){
            throw new RuntimeException("获取密保问题异常或未设置密保问题！");
        }

        return findByUserId(userInfoDTO.getId(), hideAnswer);
    }

    @Override
    public Boolean saveOfLoginUser(List<UserSecurityQuestionDTO> userSecurityQuestionDTOList, String verifyCode) {
        if(verifyCode!=null&&!kaptchaAppService.validateKaptchaFour(verifyCode)) {
            throw new ApplicationException(ErrCodeEnum.VERIFY_CODE_ERROR);
        }

        if(userSecurityQuestionDTOList.size()!=3){
            throw new RuntimeException("仅支持设置3个密保问题！");
        }

        User user = UserContext.getUser();
        Long userId = Long.valueOf(user.getUserId());

        Boolean rst = save(userSecurityQuestionDTOList, userId);

        return rst;
    }

    @Override
    public Boolean save(List<UserSecurityQuestionDTO> userSecurityQuestionDTOList, Long userId) {
        if(userId==null){
            throw new RuntimeException("userId不能为空！");
        }

        deleteByUserId(userId);
        List<UserSecurityQuestion> userSecurityQuestions = BeanUtil.copyToList(userSecurityQuestionDTOList, UserSecurityQuestion.class);
        for(UserSecurityQuestion userSecurityQuestion:userSecurityQuestions){
            userSecurityQuestion.setUserId(userId);
            userSecurityQuestionDomainService.save(userSecurityQuestion);
        }

        return true;
    }

    @Override
    public Boolean deleteByUserId(Long userId) {
        if(Objects.isNull(userId))
            return false;
        return userSecurityQuestionDomainService.deleteByUserId(userId);
    }



    @Override
    public String validateSecurityQuestion(ValidateSecurityQuestionReq validateSecurityQuestionReq) {
        String verifyCode = validateSecurityQuestionReq.getVerifyCode();

        // 验证6位验证码
        if(!kaptchaAppService.validateKaptchaSix(verifyCode)) {
            throw new ApplicationException(ErrCodeEnum.VERIFY_CODE_ERROR);
        }

        String username = validateSecurityQuestionReq.getUsername();
        if(username==null||"".equals(username)){
            throw new RuntimeException("参数输入不正确！");
        }
        UserInfoDTO userInfoDTO = userInfoAppService.getUserInfoByUserName(username);
        if(userInfoDTO==null){
            throw new RuntimeException("密保验证异常或未设置密保问题！");
        }
        Long userId = userInfoDTO.getId();
        List<UserSecurityQuestionDTO> answerQuestionList = findByUserId(userId, false);
        if(answerQuestionList==null||answerQuestionList.isEmpty()){
            throw new RuntimeException("未设置密保问题！");
        }

        List<UserSecurityQuestionDTO> userSecurityQuestionList = validateSecurityQuestionReq.getUserSecurityQuestionList();
        ImmutableMap<Long, UserSecurityQuestionDTO> reqQuestionMap = Maps.uniqueIndex(userSecurityQuestionList, UserSecurityQuestionDTO::getId);

        for(UserSecurityQuestionDTO answerQuestion:answerQuestionList){
            Long id = answerQuestion.getId();
            UserSecurityQuestionDTO userSecurityQuestion = reqQuestionMap.get(id);
            if(userSecurityQuestion==null){
                throw new RuntimeException("密保验证未通过！");
            }

            String answer = answerQuestion.getAnswer();
            String inputAnswer = userSecurityQuestion.getAnswer();

            if(!answer.equals(inputAnswer)){
                throw new RuntimeException("密保验证未通过！");
            }

        }

        String uuid = IdUtil.fastSimpleUUID();
        String key = VALIDATE_SUFFIX.concat(uuid);
        redissonUtils.set(key, username, VALIDATE_EXPIRED, TimeUnit.SECONDS);

        return uuid;
    }

    @Override
    public Boolean updatePasswordByQuestion(UpdatePasswordByQuestionReq updatePasswordByQuestionReq) {
        String validateKey = updatePasswordByQuestionReq.getValidateKey();
        String key = VALIDATE_SUFFIX.concat(validateKey);
        boolean exists = redissonUtils.exists(key);
        if(!exists){
            throw new RuntimeException("密保未验证或者验证超时！");
        }

        String username = redissonUtils.get(key);
        UserInfoDTO userInfoDTO = userInfoAppService.getUserInfoByUserName(username);
        if(userInfoDTO==null){
            throw new RuntimeException("验证失败，用户不存在！");
        }
        Long userId = userInfoDTO.getId();

        return userInfoAppService.resetPassword(userId, updatePasswordByQuestionReq.getPassword(), false);
    }
}
