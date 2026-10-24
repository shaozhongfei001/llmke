package com.gientech.ragcommon.auth.dto;

import com.alibaba.excel.annotation.ExcelProperty;
import com.alibaba.excel.annotation.write.style.ColumnWidth;
import com.gientech.start.easyexcel.dto.BaseDTO;
import lombok.Data;

@Data
public class UserExportDTO extends BaseDTO {

    @ExcelProperty("用户ID")
    @ColumnWidth(10)
    private Long userId;

    @ExcelProperty("用户登录名")
    @ColumnWidth(20)
    private String userName;

    @ExcelProperty("用户名")
    @ColumnWidth(20)
    private String userRealname;

    @ExcelProperty("邮箱")
    @ColumnWidth(20)
    private String userEmail;

    @ExcelProperty("角色")
    @ColumnWidth(25)
    private String roleNames;

    @ExcelProperty("部门")
    @ColumnWidth(25)
    private String deptName;

    @ExcelProperty("创建时间")
    @ColumnWidth(25)
//    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss",timezone = "GMT+8")
    private String gmtCreate;

    @ExcelProperty("状态")
    @ColumnWidth(10)
    private String status;


}