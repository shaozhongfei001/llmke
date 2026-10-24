package com.gientech.ragcommon.auth.dto;

import com.gientech.ragcommon.auth.enums.FrameElementTypeEnums;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * @author chenjuan
 * @date 2025/3/20 14:42
 */

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class FrameElement {
    private Long id;

    private String name;

    private FrameElementTypeEnums elementType;

    private int userCount;

    private Long parentId;

    /**
     * 部门的父部门
     */
    private String parentDeptName;

    private String userName;

    private String userRealname;

    /**
     * 用户头像
     */
    private String url;

    private String userEmail;

    private String empNo;

    /**
     * 当前部门
     */
    private String deptName;

    private List<FrameElement> children;

    public static int calculateTotalUserCount(FrameElement dept) {
        int total = dept.getUserCount();

        if (dept.getChildren() != null) {
            for (FrameElement child : dept.getChildren()) {
                total += calculateTotalUserCount(child);
            }
        }
        return total;
    }
}
