package com.gientech.ragauthservice.application.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.auth.dto.UserOperateDTO;
import com.gientech.ragcommon.auth.request.SaveUserOperateReq;
import com.gientech.ragcommon.auth.request.UpdateUserOperateReq;
import com.gientech.ragcommon.auth.request.UserOperateQueryReq;

import com.gientech.ragcommon.infrastructure.page.PageExt;
import jakarta.servlet.http.HttpServletResponse;

public interface UserOperateAppService {

    UserOperateDTO findById(Long id);

    Boolean save(SaveUserOperateReq userOperateReq);

    Boolean updateById(UpdateUserOperateReq userOperateReq);

    PageExt<UserOperateDTO> list(UserOperateQueryReq queryReq);

    Boolean deleteById(Long id);

    void exportUserOperate(String fuzzy, String start, String end, HttpServletResponse response);

}
