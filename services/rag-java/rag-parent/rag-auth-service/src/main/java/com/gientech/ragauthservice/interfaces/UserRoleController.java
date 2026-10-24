package com.gientech.ragauthservice.interfaces;

import com.gientech.ragauthservice.application.service.UserRoleAppService;
import com.gientech.ragcommon.auth.request.UserRoleUpdateReq;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * <p>
 * 角色-资源关系表 前端控制器
 * </p>
 *
 * @author wudf
 * @since 2024-06-27
 */
@Tag(name = "角色分配")
@RestController
@RequestMapping("/userRole")
public class UserRoleController {

    @Autowired
    private UserRoleAppService userRoleAppService;

    @Operation(summary = "给用户分配角色")
    @PostMapping("/setRole")
    @OperationLog(operateType = "分配用户角色")
    public Boolean setRole(@Validated UserRoleUpdateReq userRoleUpdateReq) {
        return userRoleAppService.setRole(userRoleUpdateReq);
    }

    @Operation(summary = "移除用户分配角色")
    @DeleteMapping("/removeRole")
    @OperationLog(operateType = "回收用户角色")
    public Boolean removeRole(@RequestParam("userId") Long userId, @RequestParam("roleIds") List<Long> roleIds) {
        return userRoleAppService.removeRole(userId,roleIds);
    }

    @Operation(summary = "给用户分配角色(批量)")
    @PostMapping("/setRoles")
    public Boolean setRoles(@RequestBody @Validated List<UserRoleUpdateReq> userRoleUpdateReqs) {
        return userRoleAppService.setRoles(userRoleUpdateReqs);
    }

    @Operation(summary = "分配角色")
    @PostMapping("/setUserRole")
    @OperationLog(operateType = "分配角色")
    public Boolean setUserRole(@RequestBody @Validated UserRoleUpdateReq userRoleUpdateReq) {
        return userRoleAppService.setUserRole(userRoleUpdateReq);
    }

    @Operation(summary = "移除角色")
    @PostMapping("/removeUserRole")
    @OperationLog(operateType = "移除角色")
    public Boolean removeUserRole(@Validated UserRoleUpdateReq userRoleUpdateReq) {
        return userRoleAppService.removeUserRole(userRoleUpdateReq);
    }
}
