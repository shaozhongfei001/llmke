package com.gientech.ragcommon.auth.request;

import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

/**
 * @Desc
 * @Author ZhenPanHong
 * @Date 2025/3/21 17:14
 */
@Data
public class EditDeptGroupReq {

    /**
     * 机构组id
     */
    @NotNull(message = "groupId不能为空")
    private Long groupId;

    /**
     * 部门id
     */
    @NotEmpty(message = "deptIds不能为空")
    private List<Long> deptIds;
}
