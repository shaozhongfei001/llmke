package com.gientech.ragcommon.auth.request;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class UpdateGroupReq {

    /**
     * 主键
     */
    @NotNull(message = "id不能为空")
    private Long id;

    /**
     * 父id (目前机构组只有一级)
     */
//    private Long pid;

    /**
     * 机构组名称
     */
    private String name;

    /**
     * 描述
     */
    private String description;
}
