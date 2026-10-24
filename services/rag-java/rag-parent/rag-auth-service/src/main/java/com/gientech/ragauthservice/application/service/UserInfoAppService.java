package com.gientech.ragauthservice.application.service;

import com.alibaba.excel.support.ExcelTypeEnum;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.auth.dto.ResignedUserDTO;
import com.gientech.ragcommon.auth.dto.UserImportDTO;
import com.gientech.ragcommon.auth.dto.UserInfoDTO;
import com.gientech.ragcommon.auth.request.*;
import com.gientech.start.easyexcel.result.ExcelImportResult;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;

public interface UserInfoAppService {
    /**
     * 获取验证码
     * @param request
     * @param response
     */
    void getKaptchaImage(HttpServletRequest request, HttpServletResponse response, boolean isLogin) throws IOException;

    /**
     * 用户登录
     * @param agentLoginReq
     * @param roleId
     * @return
     */
    UserInfoDTO agentLogin(AgentLoginReq agentLoginReq,Long roleId);
    /**
     * 用户登录
     * @param loginReq
     * @return
     */
    UserInfoDTO login(LoginReq loginReq);

    /**
     * 用户登录（不需要验证码）
     * @param simpleLoginReq
     * @return
     */
    UserInfoDTO simpleLogin(SimpleLoginReq simpleLoginReq);

    /**
     * 获取用户信息
     * @return
     */
    UserInfoDTO getUserInfo();

    UserInfoDTO getUserInfoById(Long userId);

    /**
     * 获取用户信息
     * @return
     */
    UserInfoDTO getUserInfoByUserName(String userName);

    /**
     * 修改用户密码
     * @param updatePasswordReq
     * @return
     */
    Boolean updatePassword(UpdatePasswordReq updatePasswordReq);

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
    UserInfoDTO updatePersonalInfo(UpdateUserInfoReq updateUserInfoReq);

    Boolean updateUseInfoBatch(UpdateUserInfoReq req);

    Boolean updateUserStatusBatch(UpdateUserInfoReq req);

    /**
     * 退出
     * @return
     */
    Boolean logout();

    /**
     * 新增用户
     * @param addUserReq
     * @return
     */
    UserInfoDTO addUser(AddUserReq addUserReq);

    /**
     * 用户注册
     * @param userRegistReq
     * @return
     */
    Boolean regist(UserRegistReq userRegistReq);

    /**
     * 启用/禁用用户
     * @param status
     * @return
     */
    Boolean setUserStatus(List<Long> userIds ,Integer status);

    /**
     * 通过条件查询用户列表
     * @param searchUserListRequest
     * @return
     */
    Page<UserInfoDTO> searchUserList(SearchUserReq searchUserListRequest);

    /**
     * 重置以用户密码
     * @param userIds
     * @return
     */
    Boolean resetPassword(List<Long> userIds);

    /**
     * 根据appKey获取用户
     *
     * @param appKey
     * @return
     */
    UserInfoDTO getUserInfoByAppKey(String appKey);

    /**
     * 批量新增用户
     * @param userBatchReqs
     * @return
     */
    Boolean addBatch(List<AddUserBatchReq> userBatchReqs);

    /**
     * 更新
     * @param updateUserReq
     * @return
     */
    Boolean update(UpdateUserReq updateUserReq);

    /**
     * 根据条件导出用户信息
     * @param deptIds
     */
    void export(List<String> deptIds,HttpServletResponse response);

    /**
     * 导出验证失败的数据
     * @param response
     */
    void exportError(HttpServletResponse response);

    /**
     * 用户数据批量导入
     * @param file
     * @param
     * @return
     */
    List<UserImportDTO> importData(MultipartFile file);

    /**
     * 下载用户导入的模板
     * @param type
     * @param response
     */
    void downloadTemplate(ExcelTypeEnum type, HttpServletResponse response);

    /**
     * 通过用户ids删除
     * @param userIds
     * @return
     */
    Boolean deleteByIds(List<Long> userIds);

    /**
     * 用户类型
     * @return
     */
    Integer getUserType();

    /**
     * 查询离职用户列表
     * @param userQueryReq
     * @return
     */
    Page<ResignedUserDTO> searchResignedUserList(UserQueryReq userQueryReq);

    /**
     * 通过角色查询用户
     * @param roleId
     * @param pageNo
     * @param pageSize
     * @return
     */
    Page<UserInfoDTO> searchUserByRole(Long roleId, Long pageNo, Long pageSize);

    /**
     * 清空离职人员
     * @return
     */
    Boolean clearResignedUsers();

    /**
     * 用户类型
     * @return
     */
    Integer getUserType(String userName);


    Boolean updateBatchUserFeature(List<Long> userIds, String feature);

    /**
     * 重置密码
     * @param isAdmin 是否是管理员操作，管理员操作记录密码到AdminResetPassword
     */
    Boolean resetPassword(Long userId, String password, Boolean isAdmin);

    /**
     * 获取管理员重置的密码
     * @return
     */
    String queryAdminResetPassword(Long userId);
}
