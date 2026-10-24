package com.gientech.ragauthservice.domain.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.gientech.ragauthservice.domain.model.DepartmentInfoDO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.LinkedList;
import java.util.List;

@Mapper
public interface DepartmentInfoMapper extends BaseMapper<DepartmentInfoDO> {

    LinkedList<DepartmentInfoDO> recursiveListById(@Param("deptId") Long deptId, @Param("depth") Integer depth);

    LinkedList<DepartmentInfoDO> recursiveListByIds(@Param("ids") List<Long> ids);

    DepartmentInfoDO findByParentNameAndName(@Param("parentDeptName")String parentDeptName, @Param("deptName")String deptName);

    int saveBatch(@Param("list") List<DepartmentInfoDO> departmentInfoDOS);
}