package com.gientech.ragauthservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.auth.request.UserOperateQueryReq;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragauthservice.domain.entity.UserOperate;
import com.gientech.ragauthservice.domain.mapper.UserOperateMapper;
import com.gientech.ragauthservice.domain.model.UserOperateDO;
import com.gientech.ragauthservice.domain.repository.UserOperateRepository;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import org.springframework.util.CollectionUtils;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Objects;

@Repository
public class  UserOperateRepositoryImpl implements  UserOperateRepository {

    @Autowired
    private  UserOperateMapper  userOperateMapper;

    @Override
    public UserOperate findById(Long id) {
        UserOperateDO userOperateDO = userOperateMapper.selectById(id);
        return Objects.isNull(userOperateDO) ? null : BeanUtil.copyProperties(userOperateDO,UserOperate.class);
    }

    @Override
    public Boolean save(UserOperate userOperate) {
//        User user = UserContext.getUser();
//        String userName = user.getUserName();
//        userOperate.setUpdateBy(userName);
//        userOperate.setCreateBy(userName);
//        userOperate.setGmtCreate(new Date());
//        userOperate.setGmtModified(userOperate.getGmtCreate());
        return userOperateMapper.insert(BeanUtil.copyProperties(userOperate, UserOperateDO.class)) > 0;
    }

    @Override
    public Boolean updateById(UserOperate userOperate) {
        if (Objects.isNull(userOperate.getId()))
            return false;
        User user = UserContext.getUser();
        String userName = user.getUserName();
//        userOperate.setUpdateBy(userName);
        userOperate.setGmtModified(new Date());
        return userOperateMapper.updateById(BeanUtil.copyProperties(userOperate, UserOperateDO.class)) > 0;
    }

    @Override
    public Page<UserOperate> list(UserOperateQueryReq queryReq) {
        Long pageNo = queryReq.getPageNo();
        Long pageSize = queryReq.getPageSize();
        String fuzzy = queryReq.getFuzzy();
        String start = queryReq.getStart();
        String end = queryReq.getEnd();

        QueryWrapper<UserOperateDO> queryWrapper = new QueryWrapper<>();
        if (StringUtils.isNotBlank(fuzzy))
            queryWrapper.and(name -> name
                    .like("user_name", fuzzy)
                    .or(id -> id.like("name", fuzzy)));

        queryWrapper.between(
                (StringUtils.isNotBlank(start) && StringUtils.isNotBlank(end)), "gmt_created",
                start + " 00:00:00", end + " 23:59:59");
        queryWrapper.orderByDesc("gmt_created");

        Page<UserOperateDO> page = new Page<>(pageNo, pageSize);
        IPage<UserOperateDO> pageResult = userOperateMapper.selectPage(page, queryWrapper);
        Page<UserOperate> listPage = new Page<>();
        BeanUtil.copyProperties(pageResult, listPage);
        listPage.setRecords(BeanUtil.copyToList(pageResult.getRecords(), UserOperate.class));
        return listPage;
    }

    @Override
    public Boolean deleteById(Long id) {
        return userOperateMapper.deleteById(id) > 0;
    }

    @Override
    public List<UserOperate> queryByCondition(String fuzzy, String start, String end) {
        QueryWrapper<UserOperateDO> queryWrapper = new QueryWrapper<>();
        if (StringUtils.isNotBlank(fuzzy))
            queryWrapper.and(name -> name
                    .like("user_name", fuzzy)
                    .or(id -> id.like("name", fuzzy)));

        queryWrapper.between(
                (StringUtils.isNotBlank(start) && StringUtils.isNotBlank(end)), "gmt_created",
                start + " 00:00:00", end + " 23:59:59");
        queryWrapper.orderByDesc("gmt_created");
        List<UserOperateDO> userOperateDOS = userOperateMapper.selectList(queryWrapper);

        return BeanUtil.copyToList(userOperateDOS, UserOperate.class);
    }

    @Override
    public Integer queryfailTotal(UserOperateQueryReq queryReq) {
        String fuzzy = queryReq.getFuzzy();
        String start = queryReq.getStart();
        String end = queryReq.getEnd();

        QueryWrapper<UserOperateDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("success",0);
        if (StringUtils.isNotBlank(fuzzy))
            queryWrapper.and(name -> name
                    .like("user_name", fuzzy)
                    .or(id -> id.like("name", fuzzy)));

        queryWrapper.between(
                (StringUtils.isNotBlank(start) && StringUtils.isNotBlank(end)), "gmt_created",
                start + " 00:00:00", end + " 23:59:59");
        queryWrapper.orderByDesc("gmt_created");
        List<UserOperateDO> userOperateDOS = userOperateMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(userOperateDOS) ? 0 : userOperateDOS.size();
    }
}
