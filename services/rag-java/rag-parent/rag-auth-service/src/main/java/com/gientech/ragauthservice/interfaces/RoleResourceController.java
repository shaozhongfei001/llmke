package com.gientech.ragauthservice.interfaces;

import com.gientech.ragauthservice.application.service.RoleResourceAppService;
import com.gientech.ragauthservice.interfaces.dto.RoleResourceDTO;
import com.gientech.ragauthservice.interfaces.req.SaveRoleResourceReq;
import com.gientech.ragauthservice.interfaces.req.UpdateRoleResourceReq;
import io.swagger.v3.oas.annotations.Operation;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/roleResource")
public class RoleResourceController {

    private final RoleResourceAppService roleResourceAppService;

    public RoleResourceController(RoleResourceAppService roleResourceAppService) {
        this.roleResourceAppService = roleResourceAppService;
    }

    @Operation(summary = "获取角色下的资源")
    @GetMapping
    public Set<Long> listByRoleId(@RequestParam("roleId") Long roleId) {
        return roleResourceAppService.listByRoleId(roleId).stream().map(RoleResourceDTO::getResourceId).filter(Objects::nonNull).collect(Collectors.toSet());
    }

    @Operation(summary = "添加角色-资源关联")
    @PostMapping
    public Boolean addRoleResource(@RequestBody @Valid SaveRoleResourceReq req) {
        return roleResourceAppService.addRoleResource(req.getRoleId(), req.getResourceIds());
    }

    @Operation(summary = "删除角色-资源关联")
    @PutMapping
    public Boolean deleteRoleResources(@RequestBody @Valid UpdateRoleResourceReq req) {
        return roleResourceAppService.delRoleResource(req.getRoleId(), req.getResourceIds());
    }
}
