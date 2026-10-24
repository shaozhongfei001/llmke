package com.gientech.ragcommon.auth.request;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

//@Schema(name = "检索角色列表请求参数")
@Data
public class SearchRoleListReq {

    //@Schema(name = "status",description = "用户状态 0 禁用 1启用")
    private Integer status;

    //@Schema(name = "idOrName",description = "用户id或用户名")
    private String idOrName;

    //@Schema(name = "pageNo",description = "第几页 默认值 1")
    private Long pageNo = 1L;

    //@Schema(name = "pageSize",description = "每页大小 默认值 20")
    private Long pageSize = 20L;
}
