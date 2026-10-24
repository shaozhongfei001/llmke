package com.gientech.ragcommon.auth.request;

import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

@Data
public class EditUserGroupReq {

    /**
     * 机构组id
     */
    @NotNull(message = "groupId不能为空")
    private Long groupId;

    /**
     * 用户id
     */
    @NotEmpty(message = "userIds不能为空")
    private List<Long> userIds;
}
