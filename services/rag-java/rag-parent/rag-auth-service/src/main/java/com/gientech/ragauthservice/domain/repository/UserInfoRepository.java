package com.gientech.ragauthservice.domain.repository;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.UserInfo;
import com.gientech.ragauthservice.domain.entity.UserInfoExt;
import com.gientech.ragcommon.auth.request.SearchUserReq;
import com.gientech.ragcommon.auth.request.UserQueryReq;

import java.util.List;

public interface UserInfoRepository {

    UserInfo getByUserName(String userName);

    void updateByPrimaryKey(UserInfo user);

    UserInfo getUserInfoById(Long userId);

    List<UserInfo> getUserListByIds(List<Long> userIds);

    Long addUserInfo(UserInfo userInfo);

    Boolean setUserStatus(List<Long> userIds, Integer status);

    Page<UserInfo> list(SearchUserReq searchUserListRequest);

    List<UserInfo> getUserInfoByIds(List<Long> userIds);

    UserInfo getUserInfoByAppKey(String appKey);

    List<UserInfo> inserBatch(List<UserInfo> userInfoList);

    int updateBatch(List<Long> ids, String deptId, String deptName, Integer status);

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
