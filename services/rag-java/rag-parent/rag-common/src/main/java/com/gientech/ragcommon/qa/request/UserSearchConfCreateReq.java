package com.gientech.ragcommon.qa.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;
import java.util.List;

@Schema(name = "新增用户检索配置请求参数",requiredProperties = {"userIds","confId"})
@Data
public class UserSearchConfCreateReq {

    @Schema(name = "userIds",description = "用户id")
    @NotEmpty(message = "userIds不能为空")
    private List<Long> userIds;

    @Schema(name = "confId",description = "配置id")
    @NotNull(message = "confId不能为空")
    private Long confId;
}
