package com.gientech.ragauthservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.gientech.ragauthservice.domain.entity.UserPrivilege;
import com.gientech.ragauthservice.domain.mapper.UserPrivilegeMapper;
import com.gientech.ragauthservice.domain.model.UserPrivilegeDO;
import com.gientech.ragauthservice.domain.repository.UserPrivilegeRepository;
import com.gientech.ragauthservice.infrastructure.convertor.UserPrivilegeConvertor;
import com.gientech.ragcommon.auth.dto.PrivilegeDTO;
import com.gientech.ragcommon.auth.enums.UserPrivilegeIsDelEnums;
import com.gientech.ragcommon.auth.request.UpdateUserPermissionReq;
import com.gientech.ragcommon.auth.request.UserPrivilegeReq;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import org.apache.commons.compress.utils.Lists;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import org.springframework.util.CollectionUtils;

import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.Objects;

@Repository
public class UserPrivilegeRepositoryImpl implements UserPrivilegeRepository {

    @Autowired
    private UserPrivilegeMapper userPrivilegeMapper;

    @Override
    public void delete(Integer bizType, Long targetId, List<Long> userIds) {
        if (Objects.isNull(bizType) || Objects.isNull(targetId) || CollectionUtils.isEmpty(userIds))
            return;
        QueryWrapper<UserPrivilegeDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("biz_type", bizType)
                .eq("target_id", targetId)
                .in("user_id", userIds);
        UserPrivilegeDO userPrivilegeDO = new UserPrivilegeDO();
        userPrivilegeDO.setIsDel(UserPrivilegeIsDelEnums.YES.getCode());
        userPrivilegeMapper.update(userPrivilegeDO,queryWrapper);
    }

    @Override
    public void deleteByUserId(Integer bizType, List<Long> userIds) {
        if (Objects.isNull(bizType) || CollectionUtils.isEmpty(userIds))
            return;
        QueryWrapper<UserPrivilegeDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("biz_type", bizType)
                .in("user_id", userIds);

        UserPrivilegeDO userPrivilegeDO = new UserPrivilegeDO();
        userPrivilegeDO.setIsDel(UserPrivilegeIsDelEnums.YES.getCode());
        userPrivilegeMapper.update(userPrivilegeDO,queryWrapper);
    }

    @Override
    public void addBatch(UserPrivilegeReq userPrivilegeReq) {

        Integer bizType = userPrivilegeReq.getBizType();
        List<Long> userIds = userPrivilegeReq.getUserIds();
        Integer permission = userPrivilegeReq.getPermission();
        Long targetId = userPrivilegeReq.getTargetId();

        User user = UserContext.getUser();
        String userName = user.getUserName();
        Date date = new Date();

        List<UserPrivilegeDO> userPrivilegeDOS = Lists.newArrayList();
        userIds.forEach(userId -> {
            UserPrivilegeDO userPrivilege = new UserPrivilegeDO();
            userPrivilege.setUserId(userId);
            userPrivilege.setBizType(bizType);
            userPrivilege.setTargetId(targetId);
            userPrivilege.setPermission(permission);
            userPrivilege.setUpdateBy(userName);
            userPrivilege.setCreateBy(userName);
            userPrivilege.setGmtModified(date);
            userPrivilege.setGmtCreate(date);
            userPrivilegeDOS.add(userPrivilege);
        });
        userPrivilegeMapper.saveBatch(userPrivilegeDOS);
    }

    @Override
    public void addBatchWithList(List<UserPrivilege> userPrivileges) {
        List<UserPrivilegeDO> userPrivilegeDOS = UserPrivilegeConvertor.INSTANCE.userPrivilege2DOS(userPrivileges);
        userPrivilegeMapper.saveBatch(userPrivilegeDOS);
    }

    @Override
    public int updatePermissionBatch(List<Long> ids, Integer permission, Long elementId) {
        if (CollUtil.isEmpty(ids)) {
            return 0;
        }
        return userPrivilegeMapper.updatePermissionBatch(ids, permission, elementId);
    }

    @Override
    public List<PrivilegeDTO> getPermission(Long userId, Integer bizType, Long targetId) {
        return userPrivilegeMapper.getPermission(userId, bizType, targetId);
    }

    @Override
    public Boolean deleteById(Long id) {
        if (Objects.isNull(id))
            return false;
        UserPrivilegeDO userPrivilegeDO = new UserPrivilegeDO();
        userPrivilegeDO.setId(id);
        userPrivilegeDO.setIsDel(UserPrivilegeIsDelEnums.YES.getCode());
        return userPrivilegeMapper.updateById(userPrivilegeDO) > 0;
    }

    @Override
    public UserPrivilege findbyCondtion(UpdateUserPermissionReq userPermissionReq) {
        Long userId = userPermissionReq.getUserId();
        Integer bizType = userPermissionReq.getBizType();
        Long targetId = userPermissionReq.getTargetId();
        QueryWrapper<UserPrivilegeDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("biz_type", bizType)
                .eq("target_id", targetId)
                .eq("is_del", UserPrivilegeIsDelEnums.NO.getCode())
                .eq("user_id", userId)
                .eq(Objects.nonNull(userPermissionReq.getPermission()), "permission", userPermissionReq.getPermission())
                .last("limit 1");
        UserPrivilegeDO userPrivilegeDO = userPrivilegeMapper.selectOne(queryWrapper);
        return Objects.isNull(userPrivilegeDO) ? null : BeanUtil.copyProperties(userPrivilegeDO, UserPrivilege.class);
    }

    @Override
    public Boolean updateById(UserPrivilege userPrivilege) {
        userPrivilege.setGmtModified(new Date());
        userPrivilege.setUpdateBy(UserContext.getUser().getUserName());
        return userPrivilegeMapper.updateById(BeanUtil.copyProperties(userPrivilege, UserPrivilegeDO.class)) > 0;
    }

    @Override
    public Boolean updateByMap(UserPrivilege userPrivilege, Map<String, Object> params) {
        QueryWrapper<UserPrivilegeDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("user_id", params.get("userId"));
        queryWrapper.eq("biz_type", params.get("bizType"));
        UserPrivilegeDO privilegeDO = BeanUtil.copyProperties(userPrivilege, UserPrivilegeDO.class);
        return userPrivilegeMapper.update(privilegeDO, queryWrapper) > 0;
    }

    @Override
    public List<UserPrivilege> findbyTypeAndId(Integer bizType, Long targetId) {
        if (Objects.isNull(bizType) || Objects.isNull(targetId))
            return null;
        QueryWrapper<UserPrivilegeDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("biz_type", bizType)
                .eq("is_del", UserPrivilegeIsDelEnums.NO.getCode())
                .eq("target_id", targetId);
        List<UserPrivilegeDO> userPrivilegeDOS = userPrivilegeMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(userPrivilegeDOS) ? Lists.newArrayList() : BeanUtil.copyToList(userPrivilegeDOS, UserPrivilege.class);
    }

    @Override
    public List<UserPrivilege> list(UserPrivilege queryParam) {
        LambdaQueryWrapper<UserPrivilegeDO> wrapper = Wrappers.lambdaQuery(UserPrivilegeDO.class)
                .eq(Objects.nonNull(queryParam.getId()), UserPrivilegeDO::getUserId, queryParam.getUserId())
                .eq(Objects.nonNull(queryParam.getBizType()), UserPrivilegeDO::getBizType, queryParam.getBizType())
                .in(!CollectionUtils.isEmpty(queryParam.getTargetIds()), UserPrivilegeDO::getTargetId, queryParam.getTargetIds())
                .eq(Objects.nonNull(queryParam.getPermission()), UserPrivilegeDO::getPermission, queryParam.getPermission())
                .eq(Objects.nonNull(queryParam.getUserId()), UserPrivilegeDO::getUserId, queryParam.getUserId())
                .eq(UserPrivilegeDO::getIsDel, UserPrivilegeIsDelEnums.NO.getCode())
                .eq(Objects.nonNull(queryParam.getCreateBy()), UserPrivilegeDO::getCreateBy, queryParam.getCreateBy())
                .orderByDesc(UserPrivilegeDO::getGmtCreate);

        List<UserPrivilegeDO> userPrivilegeDOS = userPrivilegeMapper.selectList(wrapper);
        return CollUtil.isEmpty(userPrivilegeDOS) ? Lists.newArrayList() : BeanUtil.copyToList(userPrivilegeDOS, UserPrivilege.class);
    }

    @Override
    public List<Integer> getTransferType(Long userId, String userName) {
        List<Integer> transferTypes = userPrivilegeMapper.getTransferType(userId, userName);
        return CollUtil.isEmpty(transferTypes) ? Lists.newArrayList() : transferTypes;
    }
}
