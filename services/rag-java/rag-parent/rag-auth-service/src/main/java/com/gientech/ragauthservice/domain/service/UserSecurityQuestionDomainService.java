package com.gientech.ragauthservice.domain.service;

import com.gientech.ragauthservice.domain.entity.UserSecurityQuestion;

import java.util.List;

public interface UserSecurityQuestionDomainService {

    Long countByUserId(Long userId);

    List<UserSecurityQuestion> findByUserId(Long userId);

    Boolean save(UserSecurityQuestion userSecurityQuestion);

    Boolean deleteByUserId(Long userId);
}
