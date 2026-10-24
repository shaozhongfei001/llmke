package com.gientech.ragauthservice.interfaces.req;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

@Schema(name = "保存请求参数")
@Data
public class SaveRoleResourceReq {


    @Schema(name = "roleId", description = "角色id")
    @NotNull
    private Long roleId;

    @Schema(name = "resourceIds", description = "资源ids")
    @NotEmpty
    private List<Long> resourceIds;

}
