package com.gientech.ragcommon.auth.request;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class AddGroupReq {

    /**
     * 父id (目前机构组只有一级)
     */
//    private Long pid;

    /**
     * 机构组名称
     */
    @NotBlank(message = "name不能为空")
    private String name;

    /**
     * 描述
     */
    private String description;
}
