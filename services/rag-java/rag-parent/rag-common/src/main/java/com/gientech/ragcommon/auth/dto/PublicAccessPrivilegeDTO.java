package com.gientech.ragcommon.auth.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * @Desc 所有人访问权限DTO
 * @Author ZhenPanHong
 * @Date 2025/3/11 23:55
 */
@Schema(name = "所有人访问权限")
@Data
public class PublicAccessPrivilegeDTO {

    @Schema(name = "id", description = "权限ID")
    private Long id;

    @Schema(name = "targetId", description = "配置id")
    private Long targetId;

    @Schema(name = "bizType", description = "1:知识库;2:检索配置;3:模型")
    private Integer bizType;

    @Schema(name = "permission", description = "0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限")
    private Integer permission;

    @Schema(name = "isPublicAccess", description = "是否所有人可以访问")
    private Boolean isPublicAccess;

}
