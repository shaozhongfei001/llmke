package com.gientech.ragauthservice.domain.service;


import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.RoleInfo;
import com.gientech.ragcommon.auth.dto.RoleInfoDTO;

import java.util.List;

/**
 * <p>
 * 角色表 服务类
 * </p>
 *
 * @author wudf
 * @since 2024-06-26
 */
public interface RoleInfoDomainService  {

    RoleInfo queryByName(String roleName);

    Boolean addRole(RoleInfo roleInfo);

    boolean updateRole(RoleInfo roleInfo);

    Boolean deleteRole(Long roleId);

    Page<RoleInfo> list(String idOrName, Integer status, Long pageNo, Long pageSize);

    List<RoleInfo> queryByIds(List<Long> roleIds);

    RoleInfo queryById(Long roleId,String roleName);

    RoleInfo queryById(Long roleId);

    RoleInfo getRoleInfo(Long roleId);

    List<RoleInfo> listAll();
}
