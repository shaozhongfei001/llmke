package com.gientech.ragauthservice.interfaces;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.application.service.GroupAppService;
import com.gientech.ragcommon.auth.dto.FrameElement;
import com.gientech.ragcommon.auth.dto.GroupDTO;
import com.gientech.ragcommon.auth.dto.UserInfoDTO;
import com.gientech.ragcommon.auth.request.*;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * <p>
 * 机构组 前端控制器
 * </p>
 *
 * @author wudf
 * @since 2024-07-23
 */
@Tag(name = "机构组")
@RestController
@RequestMapping("/group")
public class GroupController {

    @Autowired
    private GroupAppService authDataGroupAppService;

    @Operation(summary = "新增")
    @PostMapping("/add")
    @OperationLog(operateType = "创建分组")
    public Boolean addGroup(@RequestBody @Validated AddGroupReq addGroupReq) {
        return authDataGroupAppService.addGroup(addGroupReq);
    }

    @Operation(summary = "更新")
    @PutMapping("/update")
    @OperationLog(operateType = "创建分组")
    public Boolean updateGroup(@RequestBody @Validated UpdateGroupReq updateGroupReq) {
        return authDataGroupAppService.updateGroup(updateGroupReq);
    }

    @Operation(summary = "通过id删除")
    @DeleteMapping("/delete")
    @OperationLog(operateType = "删除分组")
    public Boolean deleteGroup(@RequestParam("id") Long id) {
        return authDataGroupAppService.deleteGroup(id);
    }

    @Operation(summary = "机构组列表")
    @GetMapping("/list")
    @OperationLog(operateType = "查询分组列表")
    public Page<GroupDTO> list(SearchGroupReq searchGroupReq) {
        return authDataGroupAppService.list(searchGroupReq);
    }

    @Operation(summary = "通过id获取详情")
    @GetMapping("/getGroupById")
    @OperationLog(operateType = "查看分组详情")
    public GroupDTO getGroupById(@RequestParam("id") Long id) {
        return authDataGroupAppService.getGroupById(id);
    }

    @Operation(summary = "编辑机构组的用户成员")
    @PostMapping("/editGroupUsers")
    @OperationLog(operateType = "编辑分组用户")
    public Boolean editGroupUsers(@RequestBody List<EditUserGroupReq> reqs) {
        return authDataGroupAppService.editGroupUsers(reqs);
    }

    @Operation(summary = "新增用户到指定的机构组中")
    @PostMapping("/addGroupUsers")
    @OperationLog(operateType = "新增用户到指定的机构组中")
    public Boolean addGroupUsers(@RequestBody EditUserGroupReq req) {
        return authDataGroupAppService.addGroupUsers(req);
    }

    @Operation(summary = "编辑机构组的部门成员")
    @PostMapping("/editGroupDepartments")
    @OperationLog(operateType = "编辑分组部门")
    public Boolean editGroupDepartments(@RequestBody List<EditDeptGroupReq> reqs) {
        return authDataGroupAppService.editGroupDepartments(reqs);
    }

    @Operation(summary = "批量删除机构组的成员")
    @DeleteMapping("/deleteByIds")
    @OperationLog(operateType = "批量删除机构组的成员")
    public Boolean deleteGroupMembers(@RequestBody GroupQueryReq req) {
        return authDataGroupAppService.deleteGroupMembers(req);
    }

    @Operation(summary = "机构组成员列表")
    @GetMapping("/listGroupUsers")
    @OperationLog(operateType = "查询分组用户列表")
    public Page<UserInfoDTO> listGroupUsers(GroupUserReq groupUserReq) {
        return authDataGroupAppService.listGroupUsers(groupUserReq);
    }

    @Operation(summary = "分页展示机构组成员列表")
    @GetMapping("/listFrameElements")
    @OperationLog(operateType = "查询分组用户列表")
    public Page<FrameElement> listFrameElements(GroupUserReq req) {
        return authDataGroupAppService.listFrameElements(req);
    }

    @Operation(summary = "用户组树状列表")
    @GetMapping("/treeGroup")
    public List<FrameElement> treeGroup() {
        return authDataGroupAppService.treeGroup();
    }


}
