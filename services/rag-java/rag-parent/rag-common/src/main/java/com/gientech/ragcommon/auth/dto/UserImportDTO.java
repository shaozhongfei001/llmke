package com.gientech.ragcommon.auth.dto;

import com.alibaba.excel.annotation.ExcelIgnore;
import com.alibaba.excel.annotation.ExcelProperty;
import com.alibaba.excel.annotation.write.style.ColumnWidth;
import com.gientech.start.easyexcel.dto.BaseDTO;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import lombok.Data;

@Data
public class UserImportDTO extends BaseDTO {

    @ExcelProperty("用户登录名")
    @NotBlank(message = "用户登录名不能为空")
    @ColumnWidth(30)
    private String userName;

    @ExcelProperty("姓名")
    @NotBlank(message = "姓名不能为空")
    @ColumnWidth(30)
    private String userRealname;

    @ExcelProperty("密码")
    @NotBlank(message = "密码不能为空")
    @ColumnWidth(30)
    @Pattern(regexp = "^^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[!@#$%^&*()_+\\-=\\[\\]{};':\"\\\\|,.<>\\/?]).{8,20}$", message = "密码必须包含大小写字母和特殊字符且长度不小于8位")
    private String userPassword;

    @ExcelProperty("手机号码")
    @NotBlank(message = "手机号码不能为空")
    @ColumnWidth(30)
    @Pattern(regexp = "^((13[0-9])|(14[5-9])|(15([0-3]|[5-9]))|(16[6-7])|(17[1-8])|(18[0-9])|(19[1|3])|(19[5|6])|(19[8|9]))\\d{8}$", message = "必须是正确的国内手机号")
    private String userPhone;

    @ExcelProperty("邮箱")
    @NotBlank(message = "邮箱不能为空")
    @ColumnWidth(30)
    @Pattern(regexp = "\\w+([-+.]\\w+)*@\\w+([-.]\\w+)*\\.\\w+([-.]\\w+)*", message = "必须是正确的邮件地址")
    private String userEmail;

    @NotNull(message = "部门不能为空")
    @ExcelProperty("部门")
    @ColumnWidth(30)
    private String deptPath;

    @NotNull(message = "角色不能为空")
    @ExcelProperty("角色")
    @ColumnWidth(30)
    private String roleName;

    @ExcelIgnore
    private Long deptId;

    @ExcelIgnore
    private String deptName;

    @ExcelIgnore
    private Long roleId;
}