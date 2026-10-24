package com.gientech.ragauthservice.domain.repository;

import com.gientech.ragauthservice.domain.entity.UserSecurityQuestion;

import java.util.List;

public interface UserSecurityQuestionRepository {

    Long countByUserId(Long userId);

    List<UserSecurityQuestion> findByUserId(Long userId);

    Boolean save(UserSecurityQuestion userSecurityQuestion);

    Boolean deleteByUserId(Long userId);
}
