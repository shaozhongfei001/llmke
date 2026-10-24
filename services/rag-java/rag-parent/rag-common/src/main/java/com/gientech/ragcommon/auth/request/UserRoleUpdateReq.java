package com.gientech.ragcommon.auth.request;

import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;
import java.util.List;


@Data
public class UserRoleUpdateReq {

//    @NotNull(message = "用户id不能为空")
    private Long userId;

//    @NotEmpty(message = "roleIds不能为空")
    private List<Long> roleIds;

    private Long roleId;

    private List<Long> userIds;
}
