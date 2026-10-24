package com.gientech.ragauthservice.domain.service.impl;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.GroupInfo;
import com.gientech.ragauthservice.domain.repository.GroupInfoRepository;
import com.gientech.ragauthservice.domain.service.GroupInfoDomainService;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * <p>
 * 机构组 服务实现类
 * </p>
 *
 * @author wudf
 * @since 2024-07-23
 */
@Service
public class GroupDomainServiceImpl implements GroupInfoDomainService {

    @Autowired
    private GroupInfoRepository groupInfoRepository;

    @Override
    public GroupInfo findByName(String name) {
        if(StringUtils.isEmpty(name))
            return null;
        return groupInfoRepository.findByName(name);
    }

    @Override
    public Boolean addGroup(GroupInfo authDataGroup) {
        return groupInfoRepository.addGroup(authDataGroup);
    }

    @Override
    public Boolean updateGroup(GroupInfo authDataGroup) {
      return groupInfoRepository.updateGroup(authDataGroup);
    }

    @Override
    public GroupInfo findById(Long id) {
        if(Objects.isNull(id))
            return null;
        return groupInfoRepository.findById(id);
    }

    @Override
    public Boolean deleteGroup(Long id) {
        if(Objects.isNull(id))
            return false;
        return groupInfoRepository.deleteGroup(id);
    }

    @Override
    public Page<GroupInfo> list(String name, Long pageNo, Long pageSize) {
        return groupInfoRepository.list(name,pageNo,pageSize);
    }

    @Override
    public Map<Long, GroupInfo> findByIds(List<Long> groupIds) {
        return groupInfoRepository.findByIds(groupIds);
    }
}
