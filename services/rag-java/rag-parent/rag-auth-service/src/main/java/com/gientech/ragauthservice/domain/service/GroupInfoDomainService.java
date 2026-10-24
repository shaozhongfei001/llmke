package com.gientech.ragauthservice.domain.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.GroupInfo;

import java.util.List;
import java.util.Map;

/**
 * <p>
 * 机构组 服务类
 * </p>
 *
 * @author wudf
 * @since 2024-07-23
 */
public interface GroupInfoDomainService {

    GroupInfo findByName(String name);

    Boolean addGroup(GroupInfo authDataGroup);

    Boolean updateGroup(GroupInfo authDataGroup);

    GroupInfo findById(Long id);

    Boolean deleteGroup(Long id);

    Page<GroupInfo> list(String name, Long pageNo, Long pageSize);

    Map<Long, GroupInfo> findByIds(List<Long> groupIds);
}
