package com.gientech.ragauthservice.application.service;

import com.gientech.ragcommon.context.user.User;

public interface AuthenticateAppService {

    Boolean authenticate(String userName, String url,String method);

    User decodeToken(String token);
}
