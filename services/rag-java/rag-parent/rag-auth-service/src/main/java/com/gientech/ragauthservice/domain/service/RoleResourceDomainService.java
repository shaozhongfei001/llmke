package com.gientech.ragauthservice.domain.service;

import com.gientech.ragauthservice.domain.entity.RoleResource;
import com.gientech.ragauthservice.domain.model.RoleResourceDO;
import com.baomidou.mybatisplus.extension.service.IService;

import java.util.List;

/**
 * <p>
 * 角色-资源关系表 服务类
 * </p>
 *
 * @author wudf
 * @since 2024-06-27
 */
public interface RoleResourceDomainService {

    Boolean addRoleResource(Long roleId, List<Long> resourceIds);

    Boolean delRoleResource(Long roleId, List<Long> delResourceIds);


    List<RoleResource> listByRoleId(Long roleId);
}
