package com.gientech.ragcommon.qa.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;
import java.util.List;

@Schema(name = "新增角色检索配置请求参数",requiredProperties = {"roleIds","confId"})
@Data
public class RoleSearchConfCreateReq {

    @Schema(name = "roleIds",description = "角色id")
    @NotEmpty(message = "roleIds不能为空")
    private List<Long> roleIds;

    @Schema(name = "confId",description = "配置id")
    @NotNull(message = "confId不能为空")
    private Long confId;
}
