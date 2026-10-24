package com.gientech.ragauthservice.interfaces;

import com.gientech.ragauthservice.application.service.ResourceInfoAppService;
import com.gientech.ragcommon.auth.dto.MenuDTO;
import com.gientech.ragcommon.auth.request.AddResourceReq;
import com.gientech.ragcommon.auth.request.UpdateResourceReq;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Tag(name = "资源接口")
@RestController
@RequestMapping("/resource")
public class ResourceController {

    @Autowired
    private ResourceInfoAppService resourceInfoAppService;

    @Operation(summary = "添加资源")
    @PostMapping("/add")
    public Boolean addResource(@RequestBody @Validated AddResourceReq addResourceReq) {
        return resourceInfoAppService.addResource(addResourceReq);
    }

    @Operation(summary = "删除接口资源")
    @DeleteMapping("/delete")
    public Boolean deleteResource(@RequestParam("resourceId") Long resourceId) {
        return resourceInfoAppService.deleteResource(resourceId);
    }

    @Operation(summary = "更新资源接口")
    @PutMapping("/update")
    public Boolean updateResource(@RequestBody @Validated UpdateResourceReq updateResourceReq) {
        return resourceInfoAppService.updateResource(updateResourceReq);
    }

    @Operation(summary = "根据角色获取资源")
    @GetMapping("/getMenusByRole")
    public List<MenuDTO> getMenusByRole(@RequestParam(value = "roleId") Long roleId) {
        return resourceInfoAppService.getMenusByRole(roleId);
    }

    @Operation(summary = "获取用户的资源菜单")
    @GetMapping("/getMenusByUser")
    public List<MenuDTO> getMenusByUser() {
        return resourceInfoAppService.getMenusByUser();
    }

    @Operation(summary = "获取用户的资源菜单-新")
    @GetMapping("/getMenus")
    public List<MenuDTO> getMenus() {
        return resourceInfoAppService.getMenus();
    }

    @Operation(summary = "获取所有的资源菜单")
    @GetMapping("/getAllMenus")
    public List<MenuDTO> getAllMenus() {
        return resourceInfoAppService.getAllMenus();
    }

    @Operation(summary = "获取所有的操作资源菜单")
    @GetMapping("/getOperMenus")
    public List<MenuDTO> getOperMenus() {
        return resourceInfoAppService.listOperResources();
    }
}
