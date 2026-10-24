package com.gientech.ragauthservice.domain.service.impl;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.DepartmentInfo;
import com.gientech.ragauthservice.domain.repository.DepartmentInfoRepository;
import com.gientech.ragauthservice.domain.service.DepartmentInfoDomainService;
import com.gientech.ragcommon.auth.enums.DeptStatusEnums;
import com.gientech.ragcommon.auth.request.ListDepartmentInfoReq;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragcommon.infrastructure.exception.DomainException;
import io.micrometer.common.util.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.Date;
import java.util.LinkedList;
import java.util.List;
import java.util.Objects;

@Service
public class DepartmentInfoDomainServiceImpl implements DepartmentInfoDomainService {

    @Autowired
    private DepartmentInfoRepository departmentInfoRepository;

    @Override
    public DepartmentInfo findById(Long id) {
        return departmentInfoRepository.findById(id);
    }

    @Override
    public DepartmentInfo findByName(String name) {
        return departmentInfoRepository.findByName(name);
    }

    @Override
    public Boolean create(DepartmentInfo departmentInfo) throws DomainException {
        DepartmentInfo existedDepartment = findByName(departmentInfo.getName());
        if (Objects.nonNull(existedDepartment)) {
            throw new DomainException(ErrCodeEnum.DEPARTMENT_ALREADY_EXIST);
        }
        return departmentInfoRepository.add(departmentInfo);
    }

    @Override
    public Boolean edit(DepartmentInfo departmentInfo) throws DomainException {
        DepartmentInfo existedDepartment = findById(departmentInfo.getId());
        if (Objects.isNull(existedDepartment)) {
            throw new DomainException(ErrCodeEnum.DEPARTMENT_NON_EXIST);
        }
        return departmentInfoRepository.update(departmentInfo);
    }

    @Override
    public Page<DepartmentInfo> list(ListDepartmentInfoReq departmentInfoReq) {
        return departmentInfoRepository.list(departmentInfoReq);
    }

    @Override
    public Boolean deleteById(Long id) {
        return departmentInfoRepository.deleteById(id);
    }

    @Override
    public Boolean recursiveDeleteByIds(List<Long> ids) {
        return departmentInfoRepository.recursiveDeleteByIds(ids);
    }

    @Override
    public List<DepartmentInfo> listByIds(List<Long> ids) {
        return departmentInfoRepository.listByIds(ids);
    }

    @Override
    public List<DepartmentInfo> recursiveListById(Long deptId, Integer depth) {
        return departmentInfoRepository.recursiveListById(deptId, depth);
    }

    @Override
    public DepartmentInfo findByPidAndName(Long pid, String deptName) {
        return departmentInfoRepository.findByPidAndName(pid, deptName);
    }

    @Override
    public DepartmentInfo findByParentNameAndName(String parentName, String deptName) {
        if (StringUtils.isBlank(parentName) || StringUtils.isBlank(deptName)) {
            throw new ApplicationException(ErrCodeEnum.PARAM_IS_NULL);
        }
        return departmentInfoRepository.findByParentNameAndName(parentName, deptName);
    }

    @Override
    public Boolean saveBatch(List<DepartmentInfo> departmentInfos) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        departmentInfos.forEach(departmentInfo -> {
            departmentInfo.setStatus(DeptStatusEnums.NORMAL.getCode());
            departmentInfo.setCreateBy(userName);
            departmentInfo.setModifyBy(userName);
            departmentInfo.setGmtCreate(new Date());
            departmentInfo.setGmtModified(departmentInfo.getGmtCreate());
        });
        return departmentInfoRepository.saveBatch(departmentInfos);
    }

    @Override
    public List<DepartmentInfo> findByPids(List<Long> pids) {
        return departmentInfoRepository.findByPids(pids);
    }

    @Override
    public List<DepartmentInfo> recursiveListByIds(List<Long> deptIds) {
        return departmentInfoRepository.recursiveListByIds(deptIds);
    }
}
