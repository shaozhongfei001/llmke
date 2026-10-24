package com.gientech.ragauthservice.domain.service.impl;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.UserOperate;
import com.gientech.ragauthservice.domain.repository.UserOperateRepository;
import com.gientech.ragauthservice.domain.service.UserOperateDomainService;
import com.gientech.ragcommon.auth.request.UserOperateQueryReq;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class UserOperateDomainServiceImpl implements UserOperateDomainService {

    @Autowired
    private UserOperateRepository userOperateRepository;

    @Override
    public UserOperate findById(Long id) {
        return userOperateRepository.findById(id);
    }

    @Override
    public Boolean save(UserOperate userOperate) {
        return userOperateRepository.save(userOperate);
    }

    @Override
    public Boolean updateById(UserOperate userOperate) {
        return userOperateRepository.updateById(userOperate);
    }

    @Override
    public Page<UserOperate> list(UserOperateQueryReq queryReq) {
        return userOperateRepository.list(queryReq);
    }

    @Override
    public Boolean deleteById(Long id) {
         return userOperateRepository.deleteById(id);
    }

    @Override
    public List<UserOperate> queryByCondition(String fuzzy, String start, String end) {
        return userOperateRepository.queryByCondition(fuzzy, start, end);
    }

    @Override
    public Integer queryfailTotal(UserOperateQueryReq queryReq) {
        return userOperateRepository.queryfailTotal(queryReq);
    }
}
