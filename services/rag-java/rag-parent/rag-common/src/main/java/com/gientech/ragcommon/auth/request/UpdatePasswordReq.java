package com.gientech.ragcommon.auth.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

//@Schema(name = "更新密码",requiredProperties={"oldPassword","newPassword"})
@Data
public class UpdatePasswordReq {

    //@Schema(name = "oldPassword",description = "旧密码")
    @NotBlank(message = "旧密码不能为空")
    private String oldPassword;


    //@Schema(name = "newPassword",description = "新密码")
    @NotBlank(message = "新密码不能为空")
    private String newPassword;
}
