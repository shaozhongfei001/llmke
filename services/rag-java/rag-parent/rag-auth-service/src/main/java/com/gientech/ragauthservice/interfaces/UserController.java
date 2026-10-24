package com.gientech.ragauthservice.interfaces;

import cn.hutool.core.bean.BeanUtil;
import com.alibaba.excel.support.ExcelTypeEnum;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.application.service.KaptchaAppService;
import com.gientech.ragauthservice.application.service.UserInfoAppService;
import com.gientech.ragauthservice.interfaces.req.BatchUpdateUserFeatureRequest;
import com.gientech.ragcommon.auth.dto.ResignedUserDTO;
import com.gientech.ragcommon.auth.dto.UserImportDTO;
import com.gientech.ragcommon.auth.dto.UserInfoDTO;
import com.gientech.ragcommon.auth.enums.UserStatusEnum;
import com.gientech.ragcommon.auth.request.*;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import com.google.common.collect.Maps;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.util.CollectionUtils;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * <p>
 * 用户表 前端控制器
 * </p>
 *
 * @author wudf
 * @since 2024-06-13
 */
@Tag(name = "用户相关接口")
@RestController
@RequestMapping("/user")
public class UserController {

    @Autowired
    private UserInfoAppService userInfoAppService;
    @Autowired
    private KaptchaAppService kaptchaAppService;

    @Operation(summary = "用户登录")
    @PostMapping("/login")
    @OperationLog(operateType = "用户登陆")
    public UserInfoDTO login(@RequestBody @Validated LoginReq loginReq) {
        return userInfoAppService.login(loginReq);
    }

    @Operation(summary = "用户登录（不需要验证码）")
    @PostMapping("/simpleLogin")
    public UserInfoDTO simpleLogin(@RequestBody @Validated SimpleLoginReq simpleloginReq) {
        return userInfoAppService.simpleLogin(simpleloginReq);
    }

    @Operation(summary = "获取用户个人信息")
    @GetMapping("/getUserInfo")
    @OperationLog(operateType = "查询个人信息")
    public UserInfoDTO getUserInfo() {
        return userInfoAppService.getUserInfo();
    }

    @Operation(summary = "获取用户个人信息")
    @GetMapping("/getUserInfoById/{userId}")
    @OperationLog(operateType = "查询个人信息")
    public UserInfoDTO getUserInfo(@PathVariable("userId") Long userId) {
        return userInfoAppService.getUserInfoById(userId);
    }

    @Operation(summary = "根据用户名获取用户个人信息")
    @GetMapping("/getUserInfoByUserName/{userName}")
    @OperationLog(operateType = "根据用户名获取用户个人信息")
    public UserInfoDTO getUserInfoByUserName(@PathVariable("userName") String userName) {
        return userInfoAppService.getUserInfoByUserName(userName);
    }


    @Operation(summary = "修改用户密码")
    @PostMapping("/updatePassword")
    @OperationLog(operateType = "修改个人密码")
    public Boolean updatePassword(@RequestBody UpdatePasswordReq updatePasswordReq) {
        return userInfoAppService.updatePassword(updatePasswordReq);
    }

    @Operation(summary = "弹窗强制修改用户密码-带验证码")
    @PostMapping("/forceUpdatePassword")
    @OperationLog(operateType = "弹窗强制修改用户密码-带验证码")
    public Boolean forceUpdatePassword(@RequestBody ForceUpdatePasswordReq forceUpdatePasswordReq) {
        String verifyCode = forceUpdatePasswordReq.getVerifyCode();
        if(!kaptchaAppService.validateKaptchaFour(verifyCode)) {
            throw new ApplicationException(ErrCodeEnum.VERIFY_CODE_ERROR);
        }

        UpdatePasswordReq updatePasswordReq = BeanUtil.copyProperties(forceUpdatePasswordReq, UpdatePasswordReq.class);
        return userInfoAppService.updatePassword(updatePasswordReq);
    }

    @Operation(summary = "修改头像")
    @PostMapping("/updateHeaderPic")
    @OperationLog(operateType = "修改个人头像")
    public Map updateHeaderPicture(@RequestParam(value = "file", required = true) MultipartFile file) {
        String path = userInfoAppService.updateHeaderPicture(file);
        Map<String, String> map = Maps.newHashMap();
        map.put("headerPicPath", path);
        return map;
    }

    @Operation(summary = "修改用户信息")
    @PostMapping("/updateUserInfo")
    @OperationLog(operateType = "修改用户信息")
    public UserInfoDTO updatePersonalInfo(@RequestBody @Validated UpdateUserInfoReq updateUserInfoReq) {
        return userInfoAppService.updatePersonalInfo(updateUserInfoReq);
    }

    @Operation(summary = "批量变更用户部门")
    @PostMapping("/updateUserInfoBatch")
    @OperationLog(operateType = "批量变更用户部门")
    public Boolean updateUseInfoBatch(@RequestBody @Validated UpdateUserInfoReq req) {
        return userInfoAppService.updateUseInfoBatch(req);
    }

    @Operation(summary = "批量操作离职")
    @PostMapping("/updateUserStatusBatch")
    @OperationLog(operateType = "批量操作离职")
    public Boolean updateUserStatusBatch(@RequestBody @Validated UpdateUserInfoReq req) {
        req.setStatus(UserStatusEnum.RESIGNED.getCode());
        return userInfoAppService.updateUserStatusBatch(req);
    }

    @Operation(summary = "登出")
    @PostMapping("/logout")
    @OperationLog(operateType = "用户登出")
    public Boolean logout() {
        return userInfoAppService.logout();
    }

    @Operation(summary = "新增用户账号")
    @PostMapping("/addUser")
    @OperationLog(operateType = "新增用户")
    public UserInfoDTO addUser(@RequestBody AddUserReq addUserReq) {
        return userInfoAppService.addUser(addUserReq);
    }

    @Operation(summary = "用户注册")
    @PostMapping("/regist")
    @OperationLog(operateType = "用户注册")
    public Boolean regist(@RequestBody @Validated UserRegistReq userRegistReq) {
        return userInfoAppService.regist(userRegistReq);
//        throw new ApplicationException(ErrCodeEnum.NOT_SUPPORT_REGISTER_USER);
    }

    @Operation(summary = "启用/禁用用户账号 0:禁用 ; 1:启用")
    @PostMapping("/setUserStatus")
    @OperationLog(operateType = "启用/禁用用户")
    public Boolean setUserStatus(
            @RequestParam(name = "userIds", required = true) List<Long> userIds,
            @RequestParam(name = "status", required = true, defaultValue = "1") Integer status) {
        return userInfoAppService.setUserStatus(userIds, status);
    }

    @Operation(summary = "查询用户列表")
    @GetMapping("/searchUserList")
    @OperationLog(operateType = "查看用户列表")
    public Page<UserInfoDTO> searchUserList(SearchUserReq searchUserReq) {
        return userInfoAppService.searchUserList(searchUserReq);
    }

    @Operation(summary = "查询离职用户列表")
    @GetMapping("/searchResignedUserList")
    @OperationLog(operateType = "查询离职用户列表")
    public Page<ResignedUserDTO> searchResignedUserList(UserQueryReq userQueryReq) {
        return userInfoAppService.searchResignedUserList(userQueryReq);
    }

    @Operation(summary = "重置用户密码")
    @PostMapping("resetPassword")
    @OperationLog(operateType = "重置密码")
    public Boolean resetPassword(@RequestBody @Validated @NotEmpty List<Long> userIds) {
        return userInfoAppService.resetPassword(userIds);
    }

    @Operation(summary = "获取kaptcha验证码")
    @GetMapping("/kaptcha")
    public void getKaptchaImage(
            HttpServletRequest request,
            HttpServletResponse response) throws IOException {
        userInfoAppService.getKaptchaImage(request, response, true);
    }

    @Operation(summary = "获取注册用户时的kaptcha验证码")
    @GetMapping("/registerKaptcha")
    public void getRegisterKaptchaImage(HttpServletRequest request, HttpServletResponse response) throws Exception {
        userInfoAppService.getKaptchaImage(request, response, false);
    }

    @Operation(summary = "根据appKey获取用户")
    @GetMapping("/getUserInfoByAppKey")
    public UserInfoDTO getUserInfoByAppKey(@RequestParam("appKey") String appKey) {
        UserInfoDTO userInfoDTO = userInfoAppService.getUserInfoByAppKey(appKey);
        return userInfoDTO;
    }

    @Operation(summary = "用户数据导入")
    @PostMapping("/import")
    public List<UserImportDTO> userImport(@RequestParam("file") MultipartFile file) {
        return userInfoAppService.importData(file);
    }

    @Operation(summary = "批量新增用户")
    @PostMapping("/addBatch")
    public Boolean addBatch(@RequestBody @Validated List<AddUserBatchReq> userBatchReqs) {
        return userInfoAppService.addBatch(userBatchReqs);
    }

    @Operation(summary = "更新用户信息")
    @PostMapping("/update")
    public Boolean update(@RequestBody @Validated UpdateUserReq updateUserReq) {
        return userInfoAppService.update(updateUserReq);
    }

    @Operation(summary = "用户导入模版下载")
    @GetMapping("/downloadTemplate")
    public void downloadTemplate(@RequestParam("fileType") String fileType, HttpServletResponse response) {
        userInfoAppService.downloadTemplate(ExcelTypeEnum.valueOf(fileType.toUpperCase(Locale.ROOT)), response);
    }

    @Operation(summary = "用户信息导出")
    @GetMapping("/export")
    public void export(@RequestParam(value = "deptIds", required = false) List<String> deptIds, HttpServletResponse response) {
        userInfoAppService.export(deptIds, response);
    }

    @Operation(summary = "导出验证失败的用户数据")
    @GetMapping("/exportError")
    public void exportError(HttpServletResponse response) {
        userInfoAppService.exportError(response);
    }

    @Operation(summary = "通过id批量删除用户信息")
    @DeleteMapping("/deleteByIds")
    public Boolean deleteByIds(@RequestParam("userIds") List<Long> userIds) {
        return userInfoAppService.deleteByIds(userIds);
    }

    @Operation(summary = "清空离职人员")
    @DeleteMapping("/clearResignedUsers")
    public Boolean clearResignedUsers() {
        return userInfoAppService.clearResignedUsers();
    }

    @Operation(summary = "用户类型 1 超级管理员，null其他用户")
    @GetMapping("/getUserType")
    public Integer userType() {
        return userInfoAppService.getUserType();
    }

    @Operation(summary = "用户类型 1 超级管理员，null其他用户")
    @GetMapping("/getUserTypeByUserName")
    public Integer getUserTypeByUserName(@RequestParam(value = "userName", required = false) String userName) {
        return userInfoAppService.getUserType(userName);
    }

    @Operation(summary = "根据角色查询用户")
    @GetMapping("/searchUserByRole")
    @OperationLog(operateType = "根据角色查询用户")
    public Page<UserInfoDTO> searchUserByRole(
            @RequestParam("roleId") Long roleId,
            @RequestParam(value = "pageNo", required = false, defaultValue = "1") Long pageNo,
            @RequestParam(value = "pageSize", required = false, defaultValue = "20") Long pageSize) {
        return userInfoAppService.searchUserByRole(roleId, pageNo, pageSize);
    }

    @Operation(summary = "批量添加用户特征")
    @PostMapping("/batchUpdateUserFeature")
    @OperationLog(operateType = "批量添加用户特征")
    public Boolean batchUpdateUserFeature(@Valid @RequestBody BatchUpdateUserFeatureRequest batchUpdateUserFeatureRequest) {
        if (CollectionUtils.isEmpty(batchUpdateUserFeatureRequest.getUserIds())) {
            throw new ApplicationException(ErrCodeEnum.PARAM_IS_NULL);
        }
        return userInfoAppService.updateBatchUserFeature(batchUpdateUserFeatureRequest.getUserIds(), batchUpdateUserFeatureRequest.getFeature());
    }

}
