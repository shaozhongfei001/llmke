package com.gientech.ragauthservice.interfaces;

import com.gientech.ragauthservice.application.service.KaptchaAppService;
import com.gientech.ragauthservice.application.service.UserInfoAppService;
import com.gientech.ragauthservice.domain.service.UserRoleDomainService;
import com.gientech.ragauthservice.interfaces.req.AdminResetPasswordReq;
import com.gientech.ragcommon.auth.enums.RoleTypeEnums;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import io.swagger.v3.oas.annotations.Operation;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

/**
 * 管理员操作用户相关方法
 */
@RestController
@RequestMapping("/userAdmin")
public class UserAdminController {
    @Autowired
    private UserRoleDomainService userRoleDomainService;
    @Autowired
    private UserInfoAppService userInfoAppService;
    @Autowired
    private KaptchaAppService kaptchaAppService;

    @Operation(summary = "管理员重置密码")
    @PostMapping("/resetPassword")
    @OperationLog(operateType = "管理员重置密码")
    public Boolean resetPassword(@RequestBody AdminResetPasswordReq adminResetPasswordReq) {
        User loginUser = UserContext.getUser();
        Long loginUserId = Long.parseLong(loginUser.getUserId());
        Integer loginroleType = userRoleDomainService.getRoleType(loginUserId);
        if (!RoleTypeEnums.SUPER_ADMIN.getCode().equals(loginroleType)) {
            throw new RuntimeException("无权操作");
        }

        Long userId = adminResetPasswordReq.getUserId();
        String password = adminResetPasswordReq.getPassword();
        String verifyCode = adminResetPasswordReq.getVerifyCode();

        if(!kaptchaAppService.validateKaptchaFour(verifyCode)) {
            throw new ApplicationException(ErrCodeEnum.VERIFY_CODE_ERROR);
        }

        return userInfoAppService.resetPassword(userId, password, true);
    }

    @Operation(summary = "查看管理员重置的密码")
    @GetMapping("/queryResetPassword/{userId}/{verifyCode}")
    @OperationLog(operateType = "查看管理员重置的密码")
    public String queryResetPassword(@PathVariable("userId") Long userId,
                                     @PathVariable("verifyCode") String verifyCode) {
        User loginUser = UserContext.getUser();
        Long loginUserId = Long.parseLong(loginUser.getUserId());
        Integer loginroleType = userRoleDomainService.getRoleType(loginUserId);
        if (!RoleTypeEnums.SUPER_ADMIN.getCode().equals(loginroleType)) {
            throw new RuntimeException("无权操作");
        }

        if(!kaptchaAppService.validateKaptchaFour(verifyCode)) {
            throw new ApplicationException(ErrCodeEnum.VERIFY_CODE_ERROR);
        }

        String password = userInfoAppService.queryAdminResetPassword(userId);

        if(password==null) {
            throw new RuntimeException("无管理员重置密码或密码已被更改");
        }
        return password;
    }
}
