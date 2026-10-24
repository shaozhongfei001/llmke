package com.gientech.ragauthservice.domain.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.DepartmentInfo;
import com.gientech.ragcommon.auth.request.ListDepartmentInfoReq;
import com.gientech.ragcommon.infrastructure.exception.DomainException;

import java.util.LinkedList;
import java.util.List;

public interface DepartmentInfoDomainService {

    DepartmentInfo findById(Long id);

    DepartmentInfo findByName(String name);

    Boolean create(DepartmentInfo departmentInfo) throws DomainException;

    Boolean edit(DepartmentInfo departmentInfo) throws DomainException;

    Page<DepartmentInfo> list(ListDepartmentInfoReq departmentInfoReq);

    Boolean deleteById(Long id);

    Boolean recursiveDeleteByIds(List<Long> ids);

    List<DepartmentInfo> listByIds(List<Long> ids);

    List<DepartmentInfo> recursiveListById(Long deptId, Integer depth);

    List<DepartmentInfo> recursiveListByIds(List<Long> deptIds);

    DepartmentInfo findByPidAndName(Long pid,String deptName);

    DepartmentInfo findByParentNameAndName(String parentName,String deptName);

    Boolean saveBatch(List<DepartmentInfo> departmentInfos);

    List<DepartmentInfo> findByPids(List<Long> pids);
}
