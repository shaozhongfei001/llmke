package com.gientech.ragcommon.auth.request;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

/**
 * @Desc
 * @Author ZhenPanHong
 * @Date 2025/3/21 18:05
 */
@Data
public class GroupQueryReq {
    /**
     * 机构组id
     */
    @NotNull(message = "groupId不能为空")
    private Long groupId;

    /**
     * 用户id
     */
    private List<Long> userIds;

    /**
     * 部门id
     */
    private List<Long> deptIds;
}
