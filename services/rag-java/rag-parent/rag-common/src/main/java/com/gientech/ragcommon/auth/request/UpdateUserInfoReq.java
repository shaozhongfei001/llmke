package com.gientech.ragcommon.auth.request;

import lombok.Data;

import java.util.List;


//@Schema(name = "修改个人信息请求")
@Data
public class UpdateUserInfoReq {

    private Long id;

    private List<Long> userIds;

    //@Schema(name = "userRealname",description = "真实姓名")
    private String userRealname;

    //@Schema(name = "userPhone",description = "手机号")
    private String userPhone;

    //@Schema(name = "userEmail",description = "邮件地址")
    private String userEmail;

    //@Schema(name = "deptId",description = "部门id")
    private String deptId;

    //@Schema(name = "deptName",description = "部门名称")
    private String deptName;

    private Integer status;

}
