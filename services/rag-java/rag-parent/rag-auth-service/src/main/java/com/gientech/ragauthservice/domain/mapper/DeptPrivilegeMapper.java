package com.gientech.ragauthservice.domain.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.gientech.ragauthservice.domain.model.DeptPrivilegeDO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * @Desc 部门-数据权限关联 Mapper 接口
 * @Author ZhenPanHong
 * @Date 2025/3/11 16:44
 */
@Mapper
public interface DeptPrivilegeMapper extends BaseMapper<DeptPrivilegeDO> {

    void saveBatch(List<DeptPrivilegeDO> deptPrivilegeDOS);

    int updateBatch(@Param("ids") List<Long> ids, @Param("permission") Integer permission, @Param("elementId") Long elementId);
}
