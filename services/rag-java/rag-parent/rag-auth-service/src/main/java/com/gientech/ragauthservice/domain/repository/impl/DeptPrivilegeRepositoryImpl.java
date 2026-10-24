package com.gientech.ragauthservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.gientech.ragauthservice.domain.entity.DeptPrivilege;
import com.gientech.ragauthservice.domain.mapper.DeptPrivilegeMapper;
import com.gientech.ragauthservice.domain.model.DeptPrivilegeDO;
import com.gientech.ragauthservice.domain.repository.DeptPrivilegeRepository;
import com.gientech.ragauthservice.infrastructure.convertor.DeptPrivilegeConvertor;
import com.gientech.ragcommon.auth.enums.DeptIsDelEnums;
import com.gientech.ragcommon.auth.enums.IsDtlEnums;
import com.gientech.ragcommon.auth.request.DeptPrivilegeReq;
import com.gientech.ragcommon.auth.request.UpdateDeptPermissionReq;
import com.gientech.ragcommon.context.user.UserContext;
import org.apache.commons.compress.utils.Lists;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import org.springframework.util.CollectionUtils;

import java.util.Date;
import java.util.List;
import java.util.Objects;

/**
 * @Desc 部门-数据权限关联 资源实现类
 * @Author ZhenPanHong
 * @Date 2025/3/11 15:18
 */
@Repository
public class DeptPrivilegeRepositoryImpl implements DeptPrivilegeRepository {

    @Autowired
    private DeptPrivilegeMapper deptPrivilegeMapper;

    @Override
    public void delete(Integer bizType, Long targetId, List<Long> deptIds) {
        if (Objects.isNull(bizType) || Objects.isNull(targetId) || CollectionUtils.isEmpty(deptIds))
            return;
        LambdaQueryWrapper<DeptPrivilegeDO> queryWrapper = Wrappers.lambdaQuery(DeptPrivilegeDO.class)
                .eq(DeptPrivilegeDO::getBizType, bizType)
                .eq(DeptPrivilegeDO::getTargetId, targetId)
                .in(DeptPrivilegeDO::getDeptId, deptIds);
        DeptPrivilegeDO deptPrivilegeDO = new DeptPrivilegeDO();
        deptPrivilegeDO.setIsDel(DeptIsDelEnums.YES.getCode());
        deptPrivilegeMapper.update(deptPrivilegeDO,queryWrapper);
    }

    @Override
    public void addBatch(DeptPrivilegeReq deptPrivilegeReq) {
        List<Long> deptIds = deptPrivilegeReq.getDeptIds();
        Long targetId = deptPrivilegeReq.getTargetId();
        Integer bizType = deptPrivilegeReq.getBizType();
        Integer permission = deptPrivilegeReq.getPermission();

        List<DeptPrivilegeDO> deptPrivilegeDOS = Lists.newArrayList();
        deptIds.forEach(deptId -> {
            DeptPrivilegeDO deptPrivilege = DeptPrivilegeDO.builder()
                    .deptId(deptId)
                    .bizType(bizType)
                    .targetId(targetId)
                    .permission(permission)
                    .updateBy(UserContext.getUser().getUserName())
                    .createBy(UserContext.getUser().getUserName())
                    .gmtModified(new Date())
                    .gmtCreate(new Date())
                    .build();
            deptPrivilegeDOS.add(deptPrivilege);
        });
        deptPrivilegeMapper.saveBatch(deptPrivilegeDOS);
    }

    @Override
    public int updatePermissionBatch(List<Long> ids, Integer permission, Long elementId) {
        if (CollUtil.isEmpty(ids)) {
            return 0;
        }
        return deptPrivilegeMapper.updateBatch(ids, permission, elementId);
    }

    @Override
    public void addBatchWithList(List<DeptPrivilege> deptPrivileges) {
        deptPrivilegeMapper.saveBatch(DeptPrivilegeConvertor.INSTANCE.deptPrivileges2DOS(deptPrivileges));
    }

    @Override
    public Boolean deleteById(Long id) {
        if (Objects.isNull(id))
            return false;
        DeptPrivilegeDO deptPrivilegeDO = new DeptPrivilegeDO();
        deptPrivilegeDO.setIsDel(DeptIsDelEnums.YES.getCode());
        deptPrivilegeDO.setId(id);
        return deptPrivilegeMapper.deleteById(deptPrivilegeDO) > 0;
    }

    @Override
    public DeptPrivilege findByCondition(UpdateDeptPermissionReq deptPermissionReq) {
        Long deptId = deptPermissionReq.getDeptId();
        Integer bizType = deptPermissionReq.getBizType();
        Long targetId = deptPermissionReq.getTargetId();

        LambdaQueryWrapper<DeptPrivilegeDO> queryWrapper = Wrappers.lambdaQuery(DeptPrivilegeDO.class)
                .eq(DeptPrivilegeDO::getBizType, bizType)
                .eq(DeptPrivilegeDO::getTargetId, targetId)
                .eq(DeptPrivilegeDO::getDeptId, deptId)
                .eq(DeptPrivilegeDO::getIsDel, DeptIsDelEnums.NO.getCode())
                .last("limit 1");
        DeptPrivilegeDO deptPrivilegeDO = deptPrivilegeMapper.selectOne(queryWrapper);
        return Objects.isNull(deptPrivilegeDO) ? null : BeanUtil.copyProperties(deptPrivilegeDO, DeptPrivilege.class);
    }

    @Override
    public Boolean updateById(DeptPrivilege deptPrivilege) {
        deptPrivilege.setGmtModified(new Date());
        deptPrivilege.setUpdateBy(UserContext.getUser().getUserName());
        return deptPrivilegeMapper.updateById(BeanUtil.copyProperties(deptPrivilege, DeptPrivilegeDO.class)) > 0;
    }

    @Override
    public List<DeptPrivilege> findByTypeAndId(Integer bizType, Long targetId) {
        if (Objects.isNull(bizType) || Objects.isNull(targetId))
            return Lists.newArrayList();
        LambdaQueryWrapper<DeptPrivilegeDO> queryWrapper = Wrappers.lambdaQuery(DeptPrivilegeDO.class)
                .eq(DeptPrivilegeDO::getBizType, bizType)
                .eq(DeptPrivilegeDO::getIsDel, DeptIsDelEnums.NO.getCode())
                .eq(DeptPrivilegeDO::getTargetId, targetId);
        List<DeptPrivilegeDO> deptPrivilegeDOList = deptPrivilegeMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(deptPrivilegeDOList) ? Lists.newArrayList() : BeanUtil.copyToList(deptPrivilegeDOList, DeptPrivilege.class);
    }

    @Override
    public List<DeptPrivilege> list(DeptPrivilege queryParam) {
        LambdaQueryWrapper<DeptPrivilegeDO> wrapper = Wrappers.lambdaQuery(DeptPrivilegeDO.class)
                .eq(Objects.nonNull(queryParam.getId()), DeptPrivilegeDO::getDeptId, queryParam.getId())
                .eq(Objects.nonNull(queryParam.getBizType()), DeptPrivilegeDO::getBizType, queryParam.getBizType())
                .in(!CollectionUtils.isEmpty(queryParam.getTargetIds()), DeptPrivilegeDO::getTargetId, queryParam.getTargetIds())
                .eq(Objects.nonNull(queryParam.getDeptId()), DeptPrivilegeDO::getDeptId, queryParam.getDeptId())
                .eq(DeptPrivilegeDO::getIsDel, DeptIsDelEnums.NO.getCode())
                .orderByDesc(DeptPrivilegeDO::getGmtCreate);

        List<DeptPrivilegeDO> deptPrivilegeDOS = deptPrivilegeMapper.selectList(wrapper);
        return CollUtil.isEmpty(deptPrivilegeDOS) ? Lists.newArrayList() : BeanUtil.copyToList(deptPrivilegeDOS, DeptPrivilege.class);
    }
}
