package com.gientech.ragcommon.auth.request;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

//@Schema(name = "检索用户列表请求")
@Data
public class SearchUserReq {

    //@Schema(name = "status",description = "用户状态 0 禁用 1启用")
    private Integer status;

    //@Schema(name = "fuzzy",description = "姓名/邮箱/手机号")
    private String fuzzy;

    private Long deptId;

    //@Schema(name = "pageNo",description = "第几页 默认值 1")
    private Long pageNo = 1L;

    //@Schema(name = "pageSize",description = "每页大小 默认值 20")
    private Long pageSize = 20L;
}
