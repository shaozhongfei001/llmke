package com.gientech.ragauthservice.interfaces.req;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

@Schema(name = "更新请求参数")
@Data
public class UpdateRoleResourceReq {


    @Schema(name = "roleId", description = "角色id")
    @NotNull
    private Long roleId;

    @Schema(name = "resourceIds", description = "资源ids")
    @NotEmpty
    private List<Long> resourceIds;

}
