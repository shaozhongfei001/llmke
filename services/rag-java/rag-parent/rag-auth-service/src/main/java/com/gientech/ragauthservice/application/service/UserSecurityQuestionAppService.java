package com.gientech.ragauthservice.application.service;

import com.gientech.ragcommon.auth.dto.UserSecurityQuestionDTO;
import com.gientech.ragauthservice.interfaces.req.UpdatePasswordByQuestionReq;
import com.gientech.ragauthservice.interfaces.req.ValidateSecurityQuestionReq;

import java.util.List;

public interface UserSecurityQuestionAppService {

    Boolean isSetSecurityQuestion(Long userId);

    List<UserSecurityQuestionDTO> findByUserId(Long userId, Boolean hideAnswer);

    List<UserSecurityQuestionDTO> findByUserName(String userName, Boolean hideAnswer);

    Boolean saveOfLoginUser(List<UserSecurityQuestionDTO> userSecurityQuestionDTOList, String verifyCode);

    Boolean save(List<UserSecurityQuestionDTO> userSecurityQuestionDTOList, Long userId);

    Boolean deleteByUserId(Long userId);

    String validateSecurityQuestion(ValidateSecurityQuestionReq validateSecurityQuestionReq);

    Boolean updatePasswordByQuestion(UpdatePasswordByQuestionReq updatePasswordByQuestionReq);
}
