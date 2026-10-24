package com.gientech.ragauthservice.interfaces;

import com.gientech.ragauthservice.application.service.PrivilegeAppService;
import com.gientech.ragcommon.auth.dto.*;
import com.gientech.ragcommon.auth.enums.PrivilegeTypeEnums;
import com.gientech.ragcommon.auth.request.*;
import com.gientech.ragcommon.global.CommonResponse;
import com.gientech.ragcommon.index.dto.Collaborator;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * <p>
 * 机构-数据权限关联 前端控制器
 * </p>
 *
 * @author wudf
 * @since 2024-07-31
 */
@Tag(name = "数据权限")
@RestController
@RequestMapping("/privilege")
public class PrivilegeController {

    @Autowired
    private PrivilegeAppService privilegeAppService;

    @Operation(summary = "设置用户检索配置的数据权限")
    @PostMapping("/setUserPermission")
    @OperationLog(operateType = "设置用户检索配置的数据权限")
    public Boolean setUserPermission(@RequestBody UserPrivilegeReq userPermissionReq) {
        return privilegeAppService.setUserPrivilege(userPermissionReq);
    }

    @Operation(summary = "批量设置用户检索配置的数据权限")
    @PostMapping("/setBatchUserPermission")
    @OperationLog(operateType = "批量设置用户检索配置的数据权限")
    public Boolean setBatchUserPermission(@Valid @RequestBody List<UserPrivilegeBatchReq> userPrivilegeBatchReqs) {
        return privilegeAppService.setUserPrivilegeWithList(userPrivilegeBatchReqs);
    }

    @Operation(summary = "设置机构组检索配置的数据权限")
    @PostMapping("/setGroupPermission")
    @OperationLog(operateType = "设置分组检索配置的数据权限")
    public Boolean setGroupPermission(@Valid @RequestBody GroupPrivilegeReq groupPrivilegeReq) {
        return privilegeAppService.setGroupPrivilege(groupPrivilegeReq);
    }

    @Operation(summary = "批量设置机构组检索配置的数据权限")
    @PostMapping("/setBatchGroupPermission")
    @OperationLog(operateType = "批量设置分组检索配置的数据权限")
    public Boolean setGroupPermission(@Valid @RequestBody List<GroupPrivilegeBatchReq> groupPrivilegeBatchReqs) {
        return privilegeAppService.setGroupPrivilegeWithList(groupPrivilegeBatchReqs);
    }

    @Operation(summary = "批量设置部门数据权限")
    @PostMapping("/setBatchDeptPermission")
    @OperationLog(operateType = "批量设置部门数据权限")
    public Boolean setBatchDeptPermission(@Valid @RequestBody List<DeptPrivilegeBatchReq> deptPrivilegeBatchReqs) {
        return privilegeAppService.setDeptPrivilegeWithList(deptPrivilegeBatchReqs);
    }

    @Operation(summary = "根据bizType变更当前权限的权限")
    @PostMapping("/updateCurrentPermissionByBizType")
    @OperationLog(operateType = "根据bizType变更当前权限的权限")
    public Boolean updateCurrentPermissionByBizType(@RequestBody UpdatePermissionReq updatePermissionReq) {
        return privilegeAppService.updateCurrentPermissionByBizType(updatePermissionReq);
    }

    @Operation(summary = "获取权限数据（bizType 1:知识库;2:检索配置）")
    @GetMapping("/getPermission")
    public Map<Long, PrivilegeDTO> getPermission(@RequestParam(value = "bizType", defaultValue = "1") Integer bizType, @RequestParam(value = "userName", required = false) String userName) {
        return privilegeAppService.getPermission(bizType, userName);
    }

    @Operation(summary = "判断数据是否有权限（bizType 1:知识库;2:检索配置）")
    @GetMapping("/isPermission")
    public Boolean isPermission(@RequestParam(value = "bizType", defaultValue = "1") Integer bizType, @RequestParam("targetId") Long targetId) {
        return privilegeAppService.isPermission(bizType, targetId);
    }

    @Operation(summary = "判断数据是否有权限（bizType 1:知识库;2:检索配置）")
    @GetMapping("/api/isPermission")
    public Boolean isPermissionApi(@RequestParam(value = "bizType", defaultValue = "1") Integer bizType, @RequestParam("targetId") Long targetId) {
        return privilegeAppService.isPermission(bizType, targetId);
    }

    @Operation(summary = "获取数据权限下的分组")
    @GetMapping("/getGroups")
    @OperationLog(operateType = "查询数据权限下的分组")
    public List<GroupPrivilegeDTO> getGroup(@RequestParam(value = "bizType", defaultValue = "1") Integer bizType, @RequestParam(value = "targetId") Long targetId) {
        return privilegeAppService.getGroups(bizType, targetId);
    }

    @Operation(summary = "获取数据权限下的用户")
    @GetMapping("/getUsers")
    @OperationLog(operateType = "查询数据权限下的用户")
    public List<UserPrivilegeDTO> getUsers(@RequestParam(value = "bizType", defaultValue = "1") Integer bizType, @RequestParam(value = "targetId") Long targetId) {
        return privilegeAppService.getUsers(bizType, targetId);
    }

    @Operation(summary = "修改机构组数据权限")
    @PutMapping("/updateGroupPermission")
    @OperationLog(operateType = "修改分组数据权限")
    public Boolean updateGroupPermission(@RequestBody UpdateGroupPermissionReq groupPermissionReq) {
        return privilegeAppService.updateGroupPermission(groupPermissionReq);
    }

    @Operation(summary = "修改用户数据权限")
    @PutMapping("/updateUserPermission")
    @OperationLog(operateType = "修改用户数据权限")
    public Boolean updateUserPermission(@RequestBody UpdateUserPermissionReq userPermissionReq) {
        return privilegeAppService.updateUserPermission(userPermissionReq);
    }

    @Operation(summary = "删除机构组数据权限")
    @DeleteMapping("/deleteGroupPermission")
    @OperationLog(operateType = "删除分组数据权限")
    public Boolean deleteGroupPermission(@RequestParam("id") Long id) {
        return privilegeAppService.deleteGroupPermission(id);
    }

    @Operation(summary = "删除用户数据权限")
    @DeleteMapping("/deleteUserPermission")
    @OperationLog(operateType = "删除用户数据权限")
    public Boolean deleteUserPermission(@RequestParam("id") Long id) {
        return privilegeAppService.deleteUserPermission(id);
    }

    @Operation(summary = "设置部门数据权限")
    @PostMapping("/setDeptPermission")
    @OperationLog(operateType = "设置部门数据权限")
    public Boolean setDeptPermission(@RequestBody DeptPrivilegeReq deptPrivilegeReq) {
        return privilegeAppService.setDeptPrivilege(deptPrivilegeReq);
    }

    @Operation(summary = "删除部门数据权限")
    @DeleteMapping("/deleteDeptPermission")
    @OperationLog(operateType = "删除部门数据权限")
    public Boolean deleteDeptPermission(@RequestParam("id") Long id) {
        return privilegeAppService.deleteDeptPermission(id);
    }

    @Operation(summary = "修改部门数据权限")
    @PutMapping("/updateDeptPermission")
    @OperationLog(operateType = "修改部门数据权限")
    public Boolean updateDeptPermission(@RequestBody UpdateDeptPermissionReq updateDeptPermissionReq) {
        return privilegeAppService.updateDeptPermission(updateDeptPermissionReq);
    }

    @Operation(summary = "获取数据权限下的部门")
    @GetMapping("/getDeptList")
    @OperationLog(operateType = "获取数据权限下的部门")
    public List<DeptPrivilegeDTO> getDeptList(@RequestParam(value = "bizType") Integer bizType, @RequestParam(value = "targetId") Long targetId) {
        return privilegeAppService.getDeptList(bizType, targetId);
    }

    @Operation(summary = "获取数据权限下的所有人")
    @GetMapping("/getPublicAccess")
    @OperationLog(operateType = "查询数据权限下的用户")
    public PublicAccessPrivilegeDTO getPublicAccess(@RequestParam(value = "bizType") Integer bizType, @RequestParam(value = "targetId") Long targetId) {
        return privilegeAppService.getPublicAccess(bizType, targetId);
    }

    @Operation(summary = "获取所有权限数据")
    @GetMapping("/getAllPermission")
    public List<PrivilegeDTO> getAllPermission(@RequestParam(value = "bizType") Integer bizType, @RequestParam(value = "userName", required = false) String userName) {
        return privilegeAppService.getAllPermission(bizType, userName, null);
    }

    @Operation(summary = "获取targetId的权限数据")
    @GetMapping("/getPermissionByTargetId")
    public List<PrivilegeDTO> getPermissionByTargetId(@RequestParam(value = "bizType") Integer bizType, @RequestParam(value = "targetIds") Long[] targetIds) {
        return privilegeAppService.getPermissionByTargetId(bizType, targetIds);
    }

    @Operation(summary = "获取资源的权限用户分组")
    @GetMapping("/collaborators")
    public List<Collaborator> getCollaborators(@RequestParam("kbId") Long kbId, @RequestParam(value = "bizType") Integer bizType, @RequestParam(value = "targetId") Long targetId) {
        return privilegeAppService.getUserListGroupByPermission(kbId, bizType, targetId);
    }

    @Operation(summary = "获取数据权限下的所有人、用户、部门、用户组")
    @GetMapping("/getAllList")
    @OperationLog(operateType = "获取数据权限下的所有人、用户、部门、用户组")
    public List<AllPrivilegeDTO> getAllList(@RequestParam(value = "bizType") Integer bizType, @RequestParam(value = "targetId") Long targetId) {
        return privilegeAppService.getAllList(bizType, targetId);
    }


    @Operation(summary = "转移资产")
    @PostMapping("/transferProperty")
    @OperationLog(operateType = "转移资产")
    public Boolean transferProperty(@RequestBody List<TransferPropertyReq> reqs) throws Exception {
        return privilegeAppService.transferProperty(reqs);
    }

    @Operation(summary = "获取目前可转移的资产列表")
    @GetMapping("/transferType")
    @OperationLog(operateType = "获取目前可转移的资产列表")
    public List<PrivilegeTypeEnums> getTransferType(@RequestParam("userId") Long userId) {
        return privilegeAppService.getTransferType(userId);
    }

}
