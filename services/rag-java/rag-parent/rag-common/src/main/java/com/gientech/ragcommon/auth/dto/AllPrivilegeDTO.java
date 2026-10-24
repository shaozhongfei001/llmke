package com.gientech.ragcommon.auth.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * @Desc
 * @Author ZhenPanHong
 * @Date 2025/3/20 14:41
 */
@Schema(name = "权限信息(包括所有人、用户、用户组、部门)")
@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class AllPrivilegeDTO {

    @Schema(name = "id", description = "用户权限ID 或 用户组权限ID 或 部门权限ID")
    private Long id;

    @Schema(name = "elementType", description = "1-部门;2-用户组;3-用户")
    private Integer elementType;


    @Schema(name = "bizType", description = "1:知识库;2:检索配置;3:模型")
    private Integer bizType;


    @Schema(name = "targetId", description = "目标id")
    private Long targetId;


    @Schema(name = "permission", description = "0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限")
    private Integer permission;


    @Schema(name = "userId", description = "用户id")
    private Long userId;


    @Schema(name = "userName", description = "用户名称")
    private String userName;

    @Schema(name = "userRealname", description = "用户真实姓名")
    private String userRealname;


    @Schema(name = "deptId", description = "部门id")
    private Long deptId;


    @Schema(name = "deptName", description = "部门名称")
    private String deptName;


    @Schema(name = "groupId", description = "用户组id")
    private Long groupId;


    @Schema(name = "groupName", description = "用户组名称")
    private String groupName;


    @Schema(name = "creator", description = "是否是资源创建者")
    private Boolean creator;

}
