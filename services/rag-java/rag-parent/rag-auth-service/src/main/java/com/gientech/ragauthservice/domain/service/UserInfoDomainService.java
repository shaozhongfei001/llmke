package com.gientech.ragauthservice.domain.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.UserInfo;
import com.gientech.ragauthservice.domain.entity.UserInfoExt;
import com.gientech.ragcommon.auth.request.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;

/**
 * <p>
 * 用户表 服务类
 * </p>
 *
 * @author wudf
 * @since 2024-06-13
 */
public interface UserInfoDomainService{

    /**
     * 用户登录
     * @param loginReq
     * @return
     */
    UserInfo login(LoginReq loginReq);

    /**
     * 通过id获取用户信息
     * @param userId
     * @return
     */
    UserInfo getUserInfoById(Long userId);

    UserInfo getUserInfoByUserName(String userName);

    List<UserInfo> getUserListByIds(List<Long> userIds);

    /**
     * 修改密码
     * @param userId
     * @param oldPassword
     * @param newPassword
     * @return
     */
    Boolean updatePassword(long userId, String oldPassword, String newPassword);

    /**
     * 重置密码
     * @param userId
     * @param newPassword
     * @param isAdmin 是否是管理员操作，管理员操作记录密码到AdminResetPassword
     * @return
     */
    Boolean resetPassword(long userId, String newPassword, Boolean isAdmin);

    /**
     * 修改头像
     * @param file
     * @return
     */
    String updateHeaderPicture(MultipartFile file);

    /**
     * 修改用户信息
     * @param updateUserInfoReq
     * @return
     */
    UserInfo updatePersonalInfo(UpdateUserInfoReq updateUserInfoReq);

    Boolean updateUseInfoBatch(UpdateUserInfoReq reqs);

    /**
     * 添加用户
     * @param addUserReq
     * @return
     */
    UserInfo addUser(UserInfo addUserReq);

    /**
     * 批量添加用户并返回用户id
     * @param userInfoList
     * @return
     */
    List<UserInfo> addUsers(List<UserInfo> userInfoList);

    /**
     * 通过用户名查询
     * @param userName
     * @return
     */
    UserInfo getByUserName(String userName);

    /**
     * 注册用户
     * @param userInfo
     * @return
     */
    Long regist(UserInfo userInfo);

    /**
     * 启用/禁用用户
     * @param userIds
     * @param status
     * @return
     */
    Boolean setUserStatus(List<Long> userIds, Integer status);

    /**
     * 查询用户列表数据
     * @param searchUserListRequest
     * @return
     */
    Page<UserInfo> list(SearchUserReq searchUserListRequest);
    /**
     * 重置用户密码
     * @param userIds
     * @return
     */
    Boolean resetPassword(List<Long> userIds);

    List<UserInfo> getUserInfoByIds(List<Long> userIds);

    /**
     * 根据appKey获取用户
     *
     * @param appKey
     * @return
     */
    UserInfo getUserInfoByAppKey(String appKey);

    Boolean update(UserInfo userInfo);

    void deleteByIds(List<Long> userIds);

    List<UserInfoExt> searchUserList(List<String> deptIds);

    List<UserInfo> list(UserInfo userInfoParam);

    List<UserInfo> list(String fuzzy);

    List<UserInfo> listNoDeptUsers(UserInfo userInfoParam);

    List<UserInfo> listByDeptIds(List<Long> deptIds);

    Page<UserInfo> list(List<Long> userIds, Long pageNo, Long pageSize);

    Page<UserInfo> list(UserQueryReq userQueryReq);

    List<UserInfo> getByPhoneOrEmail(String userPhone, String userEmail);

    Boolean updateBatchUserFeature(List<Long> userIds, String feature);

    /**
     * 清除管理员设置的密码
     * @param userId
     * @return
     */
    Boolean clearAdminResetPassword(Long userId);
}
