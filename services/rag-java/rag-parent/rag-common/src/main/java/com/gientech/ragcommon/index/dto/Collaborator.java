package com.gientech.ragcommon.index.dto;

import com.gientech.ragcommon.auth.dto.SimpleUserDTO;
import com.gientech.ragcommon.index.enmus.PermissionEnums;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.Set;

/**
 * @author chenjuan
 * @date 2025/3/14 14:10
 */
@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class Collaborator implements Serializable {
    private String userType;
    private boolean creator;
    private String deptName;
    private Long deptId;
    private Integer elementType;
    private PermissionEnums permission;
    private Set<SimpleUserDTO> users;
    private Integer userCount;
    private Long id;
    private Long userId;
    private String userName;
    private String userRealname;
    private Long groupId;
    private String groupName;
}
