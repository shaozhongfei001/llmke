package com.gientech.ragauthservice.domain.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.UserOperate;
import com.gientech.ragcommon.auth.request.UserOperateQueryReq;

import java.util.List;

public interface UserOperateDomainService {

    UserOperate findById(Long id);

    Boolean save(UserOperate userOperate);

    Boolean updateById(UserOperate userOperate);

    Page<UserOperate> list(UserOperateQueryReq queryReq);

    Boolean deleteById(Long id);

    List<UserOperate> queryByCondition(String fuzzy, String start, String end);

    Integer queryfailTotal(UserOperateQueryReq queryReq);
}
