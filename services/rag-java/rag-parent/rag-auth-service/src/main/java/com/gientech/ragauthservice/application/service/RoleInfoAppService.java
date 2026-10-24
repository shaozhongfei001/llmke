package com.gientech.ragauthservice.application.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.auth.dto.RoleInfoDTO;
import com.gientech.ragcommon.auth.request.SearchRoleListReq;
import com.gientech.ragcommon.auth.request.AddRoleReq;
import com.gientech.ragcommon.auth.request.UpdateRoleReq;

import java.util.List;

public interface RoleInfoAppService {

    Boolean addRole(AddRoleReq addRoleReq);

    Boolean updateRole(UpdateRoleReq updateRoleReq);

    Boolean deleteRole(Long roleId);

    Page<RoleInfoDTO> searchRoleList(SearchRoleListReq searchRoleListReq);

    List<RoleInfoDTO> getByUserId();

    RoleInfoDTO getRoleInfo(Long roleId);

    List<RoleInfoDTO> listAll();
}
