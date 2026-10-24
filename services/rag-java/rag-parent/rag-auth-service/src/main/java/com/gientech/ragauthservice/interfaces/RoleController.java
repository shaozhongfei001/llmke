package com.gientech.ragauthservice.interfaces;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.application.service.RoleInfoAppService;
import com.gientech.ragcommon.auth.dto.RoleInfoDTO;
import com.gientech.ragcommon.auth.request.SearchRoleListReq;
import com.gientech.ragcommon.auth.request.AddRoleReq;
import com.gientech.ragcommon.auth.request.UpdateRoleReq;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@Tag(name = "角色")
@RestController
@RequestMapping("/roleInfo")
public class RoleController {

    @Autowired
    private RoleInfoAppService roleInfoAppService;

    @Operation(summary = "添加角色")
    @PostMapping("/addRole")
    @OperationLog(operateType = "创建角色")
    public Boolean addRole(@RequestBody @Validated AddRoleReq addRoleReq) {
        return roleInfoAppService.addRole(addRoleReq);
    }

    @Operation(summary = "更新角色")
    @PutMapping("/updateRole")
    @OperationLog(operateType = "编辑角色")
    public Boolean updateRole(@RequestBody @Validated UpdateRoleReq updateRoleReq) {
        return roleInfoAppService.updateRole(updateRoleReq);
    }

    @Operation(summary = "删除角色")
    @DeleteMapping("/deleteRole")
    @OperationLog(operateType = "删除角色")
    public Boolean deleteRole(@RequestParam("roleId") Long roleId) {
        return roleInfoAppService.deleteRole(roleId);
    }

    @Operation(summary = "角色列表")
    @GetMapping("/list")
    @OperationLog(operateType = "查询角色列表")
    public Page<RoleInfoDTO> list(SearchRoleListReq searchRoleListReq) {
        return roleInfoAppService.searchRoleList(searchRoleListReq);
    }

    @Operation(summary = "通过用户查询角色")
    @GetMapping("/getByUserId")
    public List<RoleInfoDTO> getByUserId() {
        return roleInfoAppService.getByUserId();
    }

    @Operation(summary = "查询角色信息")
    @GetMapping("/getRoleInfo")
    @OperationLog(operateType = "查看角色详情")
    public RoleInfoDTO getRoleInfo(@RequestParam("roleId") Long roleId) {
        return roleInfoAppService.getRoleInfo(roleId);
    }

    @Operation(summary = "列出全部角色")
    @GetMapping("/listAll")
    public List<RoleInfoDTO> listAll() {
        return roleInfoAppService.listAll();
    }

}
