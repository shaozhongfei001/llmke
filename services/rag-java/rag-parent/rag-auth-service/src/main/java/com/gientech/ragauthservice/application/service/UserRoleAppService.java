package com.gientech.ragauthservice.application.service;

import com.gientech.ragcommon.auth.request.UserRoleUpdateReq;

import java.util.List;

public interface UserRoleAppService {

    Boolean setRoles(List<UserRoleUpdateReq> userRoleUpdateReqs);

    Boolean setRole(UserRoleUpdateReq userRoleUpdateReq);

    Boolean removeRole(Long userId, List<Long> roleIds);

    Boolean setUserRole(UserRoleUpdateReq userRoleUpdateReq);

    Boolean removeUserRole(UserRoleUpdateReq userRoleUpdateReq);
}
