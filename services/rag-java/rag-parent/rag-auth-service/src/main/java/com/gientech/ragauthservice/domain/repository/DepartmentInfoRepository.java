package com.gientech.ragauthservice.domain.repository;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.DepartmentInfo;
import com.gientech.ragcommon.auth.request.ListDepartmentInfoReq;

import java.util.LinkedList;
import java.util.List;

public interface DepartmentInfoRepository {

    DepartmentInfo findById(Long id);

    DepartmentInfo findByName(String name);

    Boolean add(DepartmentInfo departmentInfo);

    Boolean update(DepartmentInfo departmentInfo);

    Page<DepartmentInfo> list(ListDepartmentInfoReq departmentInfoReq);

    Boolean deleteById(Long id);

    List<DepartmentInfo> listByIds(List<Long> ids);

    LinkedList<DepartmentInfo> recursiveListById(Long deptId, Integer depth);

    List<DepartmentInfo> recursiveListByIds(List<Long> deptIds);

    Boolean recursiveDeleteByIds(List<Long> ids);

    DepartmentInfo findByPidAndName(Long pid, String deptName);

    DepartmentInfo findByParentNameAndName(String parentName, String deptName);

    Boolean saveBatch(List<DepartmentInfo> departmentInfos);

    List<DepartmentInfo> findByPids(List<Long> pids);
}
