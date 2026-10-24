package com.gientech.ragauthservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollUtil;
import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.CollectionUtils;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.DepartmentInfo;
import com.gientech.ragauthservice.domain.mapper.DepartmentInfoMapper;
import com.gientech.ragauthservice.domain.model.DepartmentInfoDO;
import com.gientech.ragauthservice.domain.repository.DepartmentInfoRepository;
import com.gientech.ragauthservice.infrastructure.convertor.DepartmentInfoConvertor;
import com.gientech.ragcommon.auth.enums.DeptStatusEnums;
import com.gientech.ragcommon.auth.request.ListDepartmentInfoReq;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.qa.enmus.StatusEnums;
import com.google.common.collect.Lists;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;

import java.util.Date;
import java.util.LinkedList;
import java.util.List;
import java.util.Objects;

@Repository
public class DepartmentInfoRepositoryImpl implements DepartmentInfoRepository {

    @Autowired
    private DepartmentInfoMapper departmentInfoMapper;

    @Override
    public DepartmentInfo findById(Long id) {
        QueryWrapper<DepartmentInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("id", id)
                .ne("status",StatusEnums.DELETE.getCode());
        DepartmentInfoDO departmentInfoDO = departmentInfoMapper.selectOne(queryWrapper);
        return Objects.isNull(departmentInfoDO) ? null : BeanUtil.copyProperties(departmentInfoDO, DepartmentInfo.class);
    }

    @Override
    public DepartmentInfo findByName(String name) {
        QueryWrapper<DepartmentInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("name", name)
                .ne("status", StatusEnums.DELETE.getCode())
                .last("limit 1");
        DepartmentInfoDO departmentInfoDO = departmentInfoMapper.selectOne(queryWrapper);
        return Objects.isNull(departmentInfoDO) ? null : BeanUtil.copyProperties(departmentInfoDO, DepartmentInfo.class);
    }

    @Override
    public Boolean add(DepartmentInfo departmentInfo) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        departmentInfo.setModifyBy(userName);
        departmentInfo.setCreateBy(userName);
        departmentInfo.setGmtCreate(new Date());
        departmentInfo.setGmtModified(departmentInfo.getGmtCreate());
        return departmentInfoMapper.insert(BeanUtil.copyProperties(departmentInfo, DepartmentInfoDO.class)) > 0;
    }

    @Override
    public Boolean update(DepartmentInfo departmentInfo) {
        if (Objects.isNull(departmentInfo.getId()))
            return false;
        User user = UserContext.getUser();
        String userName = user.getUserName();
        departmentInfo.setModifyBy(userName);
        departmentInfo.setGmtModified(new Date());
        return departmentInfoMapper.updateById(BeanUtil.copyProperties(departmentInfo, DepartmentInfoDO.class)) > 0;
    }

    @Override
    public Page<DepartmentInfo> list(ListDepartmentInfoReq departmentInfoReq) {
        QueryWrapper<DepartmentInfoDO> queryWrapper = new QueryWrapper<>();
        if (StringUtils.isNotBlank(departmentInfoReq.getName()))
            queryWrapper.eq("name", departmentInfoReq.getName());
        if (StringUtils.isNotBlank(departmentInfoReq.getCode()))
            queryWrapper.eq("code", departmentInfoReq.getCode());
        if (Objects.nonNull(departmentInfoReq.getParentId()) && departmentInfoReq.getParentId() > 0)
            queryWrapper.eq("parent_id", departmentInfoReq.getParentId());
        if(StringUtils.isNotBlank(departmentInfoReq.getFuzzy()))
            queryWrapper.like("name", departmentInfoReq.getFuzzy());

        queryWrapper.ne("status", StatusEnums.DELETE.getCode());
        Page<DepartmentInfoDO> page = new Page<>(departmentInfoReq.getPageNo(), departmentInfoReq.getPageSize());
        Page<DepartmentInfoDO> pageResult = departmentInfoMapper.selectPage(page, queryWrapper);
        Page<DepartmentInfo> listPage = new Page<>();
        BeanUtil.copyProperties(pageResult, listPage);
        listPage.setRecords(BeanUtil.copyToList(pageResult.getRecords(), DepartmentInfo.class));
        return listPage;
    }

    @Override
    public Boolean deleteById(Long id) {
        if(Objects.isNull(id))
            return false;
        DepartmentInfoDO dept = new DepartmentInfoDO();
        dept.setStatus(StatusEnums.DELETE.getCode());
        dept.setId(id);
        return departmentInfoMapper.updateById(dept) > 0;
    }

    @Override
    public List<DepartmentInfo> listByIds(List<Long> ids) {
        if (CollUtil.isEmpty(ids))
            return Lists.newArrayList();

        LambdaQueryWrapper<DepartmentInfoDO> wrapper = Wrappers.lambdaQuery(DepartmentInfoDO.class)
                .in(DepartmentInfoDO::getId, ids);

        List<DepartmentInfoDO> departmentInfoDOS = departmentInfoMapper.selectList(wrapper);
        return CollUtil.isEmpty(departmentInfoDOS) ? Lists.newArrayList() : BeanUtil.copyToList(departmentInfoDOS, DepartmentInfo.class);

    }

    @Override
    public LinkedList<DepartmentInfo> recursiveListById(Long deptId, Integer depth) {
        LinkedList<DepartmentInfoDO> departmentInfoDOS = departmentInfoMapper.recursiveListById(deptId, depth);
        return CollUtil.isEmpty(departmentInfoDOS) ? Lists.newLinkedList() : DepartmentInfoConvertor.INSTANCE.departmentInfoDOs2DepartmentInfos(departmentInfoDOS);
    }

    @Override
    public DepartmentInfo findByPidAndName(Long pid, String deptName) {
        QueryWrapper<DepartmentInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq(!Objects.isNull(pid),"parent_id",pid)
                .eq("name",deptName)
                .ne("status", DeptStatusEnums.DELETED.getCode())
                .last("limit 1");
        DepartmentInfoDO departmentInfoDO = departmentInfoMapper.selectOne(queryWrapper);
        return Objects.isNull(departmentInfoDO) ? null : BeanUtil.copyProperties(departmentInfoDO,DepartmentInfo.class);
    }

    @Override
    public DepartmentInfo findByParentNameAndName(String parentName, String deptName) {
        DepartmentInfoDO departmentInfoDO = departmentInfoMapper.findByParentNameAndName(parentName,deptName);
        return Objects.isNull(departmentInfoDO) ? null : BeanUtil.copyProperties(departmentInfoDO,DepartmentInfo.class);
    }

    @Override
    public Boolean saveBatch(List<DepartmentInfo> departmentInfos) {
        if(CollectionUtils.isEmpty(departmentInfos))
            return false;
        List<DepartmentInfoDO> departmentInfoDOS = BeanUtil.copyToList(departmentInfos, DepartmentInfoDO.class);
        return departmentInfoMapper.saveBatch(departmentInfoDOS) > 0;
    }

    @Override
    public List<DepartmentInfo> findByPids(List<Long> pids) {
        QueryWrapper<DepartmentInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.ne("status", DeptStatusEnums.DELETED.getCode())
                .in(CollectionUtils.isNotEmpty(pids),"parent_id",pids);
        List<DepartmentInfoDO> departmentInfoDOS = departmentInfoMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(departmentInfoDOS) ? null : BeanUtil.copyToList(departmentInfoDOS,DepartmentInfo.class);
    }

    @Override
    public List<DepartmentInfo> recursiveListByIds(List<Long> deptIds) {
        LinkedList<DepartmentInfoDO> departmentInfoDOS = departmentInfoMapper.recursiveListByIds(deptIds);
        return CollUtil.isEmpty(departmentInfoDOS) ? Lists.newArrayList() : DepartmentInfoConvertor.INSTANCE.departmentInfoDOs2DepartmentInfos(departmentInfoDOS);
    }

    @Override
    public Boolean recursiveDeleteByIds(List<Long> ids) {
        List<DepartmentInfoDO> departmentInfoDOS = departmentInfoMapper.recursiveListByIds(ids);
        List<Long> deptIds = departmentInfoDOS.stream().map(DepartmentInfoDO::getId).toList();
        if(!CollectionUtils.isEmpty(deptIds)){
            Wrapper<DepartmentInfoDO> wrapper = Wrappers.lambdaQuery(DepartmentInfoDO.class)
                    .in(DepartmentInfoDO::getId, deptIds);
            DepartmentInfoDO departmentInfoDO = new DepartmentInfoDO();
            departmentInfoDO.setStatus(StatusEnums.DELETE.getCode());
            return departmentInfoMapper.update(departmentInfoDO,wrapper) > 0;
        }
        return true;
    }
}
