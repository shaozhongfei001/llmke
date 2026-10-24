package com.gientech.ragauthservice.domain.service.impl;

import com.gientech.ragauthservice.domain.entity.UserSecurityQuestion;
import com.gientech.ragauthservice.domain.repository.UserSecurityQuestionRepository;
import com.gientech.ragauthservice.domain.service.UserSecurityQuestionDomainService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class UserSecurityQuestionDomainServiceImpl implements UserSecurityQuestionDomainService {

    @Autowired
    private UserSecurityQuestionRepository userSecurityQuestionRepository;

    @Override
    public Long countByUserId(Long userId) {
        return userSecurityQuestionRepository.countByUserId(userId);
    }

    @Override
    public List<UserSecurityQuestion> findByUserId(Long userId) {
        return userSecurityQuestionRepository.findByUserId(userId);
    }

    @Override
    public Boolean save(UserSecurityQuestion userSecurityQuestion) {
        return userSecurityQuestionRepository.save(userSecurityQuestion);
    }

    @Override
    public Boolean deleteByUserId(Long userId) {
         return userSecurityQuestionRepository.deleteByUserId(userId);
    }
}
