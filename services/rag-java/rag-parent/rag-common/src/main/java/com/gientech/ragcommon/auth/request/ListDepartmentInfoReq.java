package com.gientech.ragcommon.auth.request;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * @Descrption:
 * @Author:liutaiyun
 * @Date:2025/03/06 16:46
 **/
@Schema(name = "列表查询请求参数")
@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class ListDepartmentInfoReq {

    /**
     * 部门名称
     */
    private String name;

    /**
     * 部门编码
     */
    private String code;

    /**
     * 上级部门ID
     */
    private Long parentId;

    /**
     * 第几页 默认值 1
     */
    private Long pageNo = 1L;

    /**
     * 每页大小 默认值 20
     */
    private Long pageSize = 20L;


    private String fuzzy;
}
