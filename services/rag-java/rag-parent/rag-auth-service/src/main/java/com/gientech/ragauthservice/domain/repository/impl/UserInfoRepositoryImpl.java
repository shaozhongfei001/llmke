package com.gientech.ragauthservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollUtil;
import cn.hutool.core.date.DateUtil;
import cn.hutool.core.util.BooleanUtil;
import cn.hutool.core.util.StrUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.UserInfo;
import com.gientech.ragauthservice.domain.entity.UserInfoExt;
import com.gientech.ragauthservice.domain.mapper.UserInfoMapper;
import com.gientech.ragauthservice.domain.model.UserInfoDO;
import com.gientech.ragauthservice.domain.repository.UserInfoRepository;
import com.gientech.ragcommon.auth.enums.IsDtlEnums;
import com.gientech.ragcommon.auth.enums.UserIsDelEnum;
import com.gientech.ragcommon.auth.enums.UserStatusEnum;
import com.gientech.ragcommon.auth.request.SearchUserReq;
import com.gientech.ragcommon.auth.request.UserQueryReq;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.DomainException;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.compress.utils.Lists;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import org.springframework.util.CollectionUtils;

import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;
import java.util.Objects;
import java.util.stream.Collectors;

@Slf4j
@Repository
public class UserInfoRepositoryImpl implements UserInfoRepository {

    @Autowired
    private UserInfoMapper userInfoMapper;

    @Override
    public UserInfo getByUserName(String userName) {
        QueryWrapper<UserInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("user_name", userName)
                .eq("is_dtl", UserIsDelEnum.NO.getCode());
        UserInfoDO userInfoDO = userInfoMapper.selectOne(queryWrapper);
        return Objects.isNull(userInfoDO) ? null : BeanUtil.copyProperties(userInfoDO, UserInfo.class);
    }

    @Override
    public void updateByPrimaryKey(UserInfo user) {
        user.setGmtModified(new Date());
        UserInfoDO userInfoDO = BeanUtil.copyProperties(user, UserInfoDO.class);
        userInfoMapper.updateById(userInfoDO);
    }

    @Override
    public UserInfo getUserInfoById(Long userId) {
        QueryWrapper<UserInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("id", userId)
                .eq("is_dtl", UserIsDelEnum.NO.getCode());
        UserInfoDO userInfoDO = userInfoMapper.selectOne(queryWrapper);
        return Objects.isNull(userInfoDO) ? null : BeanUtil.copyProperties(userInfoDO, UserInfo.class);
    }

    @Override
    public List<UserInfo> getUserListByIds(List<Long> userIds) {
        if (CollectionUtils.isEmpty(userIds)) {
            return Lists.newArrayList();
        }
        List<UserInfoDO> userInfoDOS = userInfoMapper.selectBatchIds(userIds);
        return CollUtil.isEmpty(userInfoDOS) ? Lists.newArrayList() : BeanUtil.copyToList(userInfoDOS, UserInfo.class);
    }

    @Override
    public Long addUserInfo(UserInfo userInfo) {
        UserInfoDO userInfoDO = BeanUtil.copyProperties(userInfo, UserInfoDO.class);
        userInfoDO.setCreateBy(userInfo.getUserName());
        userInfoDO.setUpdateBy(userInfo.getUserName());
        userInfoDO.setGmtCreate(new Date());
        userInfoDO.setGmtModified(userInfo.getGmtCreate());
        userInfoMapper.insert(userInfoDO);
        return userInfoDO.getId();
    }

    @Override
    public Boolean setUserStatus(List<Long> userIds, Integer status) {
        QueryWrapper<UserInfoDO> condtion = new QueryWrapper<>();
        condtion.in("id", userIds);
        UserInfoDO userInfoDO = new UserInfoDO();
        userInfoDO.setStatus(status);
        userInfoDO.setGmtModified(new Date());
        userInfoMapper.update(userInfoDO, condtion);
        return true;
    }

    @Override
    public Page<UserInfo> list(SearchUserReq searchUserListRequest) {
        String fuzzy = searchUserListRequest.getFuzzy();
        Integer status = searchUserListRequest.getStatus();
        Long deptId = searchUserListRequest.getDeptId();
        Long pageNo = searchUserListRequest.getPageNo();
        Long pageSize = searchUserListRequest.getPageSize();

        QueryWrapper<UserInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("is_dtl", UserIsDelEnum.NO.getCode());
        if (!Objects.isNull(status)) {
            queryWrapper.eq("status", status);
        }
        if (StringUtils.isNotBlank(fuzzy)) {
            queryWrapper
                    .and(name -> name
                            .like("user_name", fuzzy)
                            .or(userRealname -> userRealname.like("user_realname", fuzzy))
                            .or(userEmail -> userEmail.like("user_email", fuzzy))
                            .or(userPhone -> userPhone.like("user_phone", fuzzy))
                    );
        }
        if (Objects.nonNull(deptId)) {
            queryWrapper.eq("dept_id", String.valueOf(deptId));
        }
        queryWrapper.ne("status", UserStatusEnum.RESIGNED.getCode());
        queryWrapper.orderByDesc("gmt_create");
        Page<UserInfoDO> page = new Page<>(pageNo, pageSize);
        Page<UserInfoDO> pageResult = userInfoMapper.selectPage(page, queryWrapper);
        Page<UserInfo> userInfoPage = new Page<>();
        BeanUtil.copyProperties(pageResult, userInfoPage);
        List<UserInfo> userInfos = BeanUtil.copyToList(pageResult.getRecords(), UserInfo.class);
        userInfoPage.setRecords(userInfos);
        return userInfoPage;
    }

    @Override
    public List<UserInfo> getUserInfoByIds(List<Long> userIds) {
        if (CollectionUtils.isEmpty(userIds))
            return Lists.newArrayList();
        QueryWrapper<UserInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.in("id", userIds).eq("is_dtl", UserIsDelEnum.NO.getCode());
        List<UserInfoDO> userInfoDOS = userInfoMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(userInfoDOS) ? Lists.newArrayList() : BeanUtil.copyToList(userInfoDOS, UserInfo.class);
    }

    @Override
    public UserInfo getUserInfoByAppKey(String appKey) {
        QueryWrapper<UserInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("app_key", appKey).eq("is_dtl", UserIsDelEnum.NO.getCode());
        List<UserInfoDO> userInfoDOList = userInfoMapper.selectList(queryWrapper);
        if (CollectionUtils.isEmpty(userInfoDOList)) {
            return null;
        } else {
            return BeanUtil.copyProperties(userInfoDOList.get(0), UserInfo.class);
        }
    }

    @Override
    public List<UserInfo> inserBatch(List<UserInfo> userInfoList) {
        List<UserInfoDO> userInfoDOS = BeanUtil.copyToList(userInfoList, UserInfoDO.class);
        userInfoMapper.insertBatch(userInfoDOS);
        return BeanUtil.copyToList(userInfoDOS, UserInfo.class);
    }

    @Override
    public int updateBatch(List<Long> ids, String deptId, String deptName, Integer status) {
        return userInfoMapper.updateBatch(ids, deptId, deptName, status);
    }

    @Override
    public void deleteByIds(List<Long> userIds) {
        QueryWrapper<UserInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.in("id", userIds).eq("is_dtl", UserIsDelEnum.NO.getCode());
        UserInfoDO userInfoDO = new UserInfoDO();
        userInfoDO.setIsDtl(UserIsDelEnum.YES.getCode() + "");
        userInfoMapper.update(userInfoDO, queryWrapper);
    }

    @Override
    public List<UserInfoExt> searchUserList(List<String> deptIds) {
        return userInfoMapper.searchUserList(deptIds);
    }

    @Override
    public List<UserInfo> list(UserInfo userInfoParam) {
        LambdaQueryWrapper<UserInfoDO> queryWrapper = Wrappers.lambdaQuery(UserInfoDO.class)
                .eq(Objects.nonNull(userInfoParam.getId()), UserInfoDO::getId, userInfoParam.getId())
                .eq(StrUtil.isNotBlank(userInfoParam.getUserName()), UserInfoDO::getUserName, userInfoParam.getUserName())
                .eq(StrUtil.isNotBlank(userInfoParam.getUserRealname()), UserInfoDO::getUserRealname, userInfoParam.getUserRealname())
                .eq(StrUtil.isNotBlank(userInfoParam.getUserEmail()), UserInfoDO::getUserEmail, userInfoParam.getUserEmail())
                .eq(StrUtil.isNotBlank(userInfoParam.getUserPhone()), UserInfoDO::getUserPhone, userInfoParam.getUserPhone())
                .eq(StrUtil.isNotBlank(userInfoParam.getEmpNo()), UserInfoDO::getEmpNo, userInfoParam.getEmpNo())
                .eq(StrUtil.isNotBlank(userInfoParam.getDeptId()), UserInfoDO::getDeptId, userInfoParam.getDeptId())
                .eq(StrUtil.isNotBlank(userInfoParam.getDeptName()), UserInfoDO::getDeptName, userInfoParam.getDeptName())
                .eq(Objects.nonNull(userInfoParam.getStatus()), UserInfoDO::getStatus, userInfoParam.getStatus())
                .eq(UserInfoDO::getIsDtl, IsDtlEnums.NO.getCode())
                .orderByDesc(UserInfoDO::getGmtCreate);
        if (Objects.isNull(userInfoParam.getStatus())) {
            queryWrapper.ne(UserInfoDO::getStatus, UserStatusEnum.RESIGNED.getCode());
        }

        List<UserInfoDO> userInfoDOList = userInfoMapper.selectList(queryWrapper);
        return CollUtil.isEmpty(userInfoDOList) ? Lists.newArrayList() : BeanUtil.copyToList(userInfoDOList, UserInfo.class);
    }

    @Override
    public List<UserInfo> list(String fuzzy) {
        LambdaQueryWrapper<UserInfoDO> queryWrapper = Wrappers.lambdaQuery(UserInfoDO.class)
                .eq(UserInfoDO::getStatus, UserStatusEnum.ENABLED.getCode())
                .and(wrapper -> {
                            if (StrUtil.isNotBlank(fuzzy)) {
                                wrapper.like(UserInfoDO::getUserRealname, fuzzy)
                                        .or()
                                        .like(UserInfoDO::getUserEmail, fuzzy);
                            }
                        }
                );
        List<UserInfoDO> userInfoDOList = userInfoMapper.selectList(queryWrapper);
        return CollUtil.isEmpty(userInfoDOList) ? Lists.newArrayList() : BeanUtil.copyToList(userInfoDOList, UserInfo.class);
    }

    @Override
    public List<UserInfo> listNoDeptUsers(UserInfo userInfoParam) {
        LambdaQueryWrapper<UserInfoDO> queryWrapper = Wrappers.lambdaQuery(UserInfoDO.class)
                .eq(Objects.nonNull(userInfoParam.getId()), UserInfoDO::getId, userInfoParam.getId())
                .eq(StrUtil.isNotBlank(userInfoParam.getUserName()), UserInfoDO::getUserName, userInfoParam.getUserName())
                .eq(StrUtil.isNotBlank(userInfoParam.getUserRealname()), UserInfoDO::getUserRealname, userInfoParam.getUserRealname())
                .eq(StrUtil.isNotBlank(userInfoParam.getUserEmail()), UserInfoDO::getUserEmail, userInfoParam.getUserEmail())
                .eq(StrUtil.isNotBlank(userInfoParam.getUserPhone()), UserInfoDO::getUserPhone, userInfoParam.getUserPhone())
                .eq(StrUtil.isNotBlank(userInfoParam.getEmpNo()), UserInfoDO::getEmpNo, userInfoParam.getEmpNo())
                .isNull(UserInfoDO::getDeptId)
                .eq(StrUtil.isNotBlank(userInfoParam.getDeptName()), UserInfoDO::getDeptName, userInfoParam.getDeptName())
                .eq(Objects.nonNull(userInfoParam.getStatus()), UserInfoDO::getStatus, userInfoParam.getStatus())
                .eq(UserInfoDO::getIsDtl, IsDtlEnums.NO.getCode())
                .orderByDesc(UserInfoDO::getGmtCreate);


        List<UserInfoDO> userInfoDOList = userInfoMapper.selectList(queryWrapper);
        return CollUtil.isEmpty(userInfoDOList) ? Lists.newArrayList() : BeanUtil.copyToList(userInfoDOList, UserInfo.class);
    }

    @Override
    public List<UserInfo> listByDeptIds(List<Long> deptIds) {
        if (CollectionUtils.isEmpty(deptIds)) {
            return Lists.newArrayList();
        }
        return userInfoMapper.listByDeptIds(deptIds);
    }

    @Override
    public Page<UserInfo> list(List<Long> userIds, Long pageNo, Long pageSize) {
        QueryWrapper<UserInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("is_dtl", UserIsDelEnum.NO.getCode())
                .in("id", userIds)
                .orderByDesc("gmt_create");
        Page<UserInfoDO> page = new Page<>(pageNo, pageSize);
        Page<UserInfoDO> pageResult = userInfoMapper.selectPage(page, queryWrapper);
        Page<UserInfo> userInfoPage = new Page<>();
        BeanUtil.copyProperties(pageResult, userInfoPage);
        List<UserInfo> userInfos = BeanUtil.copyToList(pageResult.getRecords(), UserInfo.class);
        userInfoPage.setRecords(userInfos);
        return userInfoPage;
    }

    @Override
    public Page<UserInfo> list(UserQueryReq userQueryReq) {
        // 日期格式化
        SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd");

        LambdaQueryWrapper<UserInfoDO> queryWrapper = Wrappers.lambdaQuery(UserInfoDO.class)
                .eq(Objects.nonNull(userQueryReq.getStatus()), UserInfoDO::getStatus, userQueryReq.getStatus())
                .like(StrUtil.isNotBlank(userQueryReq.getUserName()), UserInfoDO::getUserName, userQueryReq.getUserName())
                .like(StrUtil.isNotBlank(userQueryReq.getUserRealname()), UserInfoDO::getUserRealname, userQueryReq.getUserRealname())
                .eq(UserInfoDO::getIsDtl, IsDtlEnums.NO.getCode())
                .orderByDesc(BooleanUtil.isTrue(userQueryReq.getOrderByResignDate()) ? UserInfoDO::getResignDate : UserInfoDO::getGmtCreate);

        try {
            if (StrUtil.isNotBlank(userQueryReq.getStartTime()))
                queryWrapper.ge(UserInfoDO::getResignDate, DateUtil.beginOfDay(dateFormat.parse(userQueryReq.getStartTime())));
            if (StrUtil.isNotBlank(userQueryReq.getEndTime()))
                queryWrapper.le(UserInfoDO::getResignDate, DateUtil.endOfDay(dateFormat.parse(userQueryReq.getEndTime())));
        } catch (ParseException e) {
            log.error("起始日期或终止日期格式不正确", e);
            throw new DomainException(ErrCodeEnum.TIME_FORMAT_ERROR);
        }

        Page<UserInfoDO> page = new Page<>(userQueryReq.getPageNo(), userQueryReq.getPageSize());
        Page<UserInfoDO> pageResult = userInfoMapper.selectPage(page, queryWrapper);
        Page<UserInfo> userInfoPage = new Page<>();
        BeanUtil.copyProperties(pageResult, userInfoPage);
        List<UserInfo> userInfos = BeanUtil.copyToList(pageResult.getRecords(), UserInfo.class);
        userInfoPage.setRecords(userInfos);
        return userInfoPage;
    }

    @Override
    public List<UserInfo> getByPhoneOrEmail(String userPhone, String userEmail) {
        QueryWrapper<UserInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("is_dtl", UserIsDelEnum.NO.getCode())
                .and(wrapper -> wrapper.eq("user_phone", userPhone)
                        .or()
                        .eq("user_email", userEmail));
        List<UserInfoDO> userInfoDOList = userInfoMapper.selectList(queryWrapper);
        return CollUtil.isEmpty(userInfoDOList) ? Lists.newArrayList() : BeanUtil.copyToList(userInfoDOList, UserInfo.class);
    }

    @Override
    public Boolean updateBatchUserFeature(List<Long> userIds, String feature) {
        return userInfoMapper.updateBatchUserFeature(userIds, feature) > 0;
    }

    @Override
    public Boolean clearAdminResetPassword(Long userId) {
        return userInfoMapper.clearAdminResetPassword(userId) > 0;
    }
}
