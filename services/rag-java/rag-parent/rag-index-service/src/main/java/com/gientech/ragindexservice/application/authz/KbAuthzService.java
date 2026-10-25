package com.gientech.ragindexservice.application.authz;

import com.gientech.ragcommon.auth.enums.RoleTypeEnums;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.enmus.PermissionEnums;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragindexservice.application.remote.UserClient;
import com.gientech.ragindexservice.domain.service.KnowledgeBaseDomainService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

/**
 * R13-SEC-A1：知识库对象级授权。
 * <p>
 * 授权口径完全复用原工程语义（{@code knowledge_base} + {@code user_privilege} / {@code dept_privilege} /
 * {@code group_privilege}，取 MAX(permission)），不新造权限模型：
 * <ul>
 *     <li>0 无权限 / 1 可阅读 / 2 可编辑 / 3 可管理</li>
 *     <li>超级管理员视为 3（原 {@code RoleTypeEnums.SUPER_ADMIN} 口径）</li>
 *     <li>属主权限由 mapper 中 create_by 分支给出，不在本类重复判断</li>
 * </ul>
 * 仅做"主体 + 资源 + 动作"三元组校验；撤权后因为每次实时查库，缓存失效由原缓存注解负责。
 */
@Slf4j
@Component
public class KbAuthzService {

    /** 读：查看知识库、文件、分块、引用、下载、问答 */
    public static final int ACT_READ = PermissionEnums.READ.getCode();
    /** 写：编辑配置、重解析、上传、删除文件 */
    public static final int ACT_WRITE = PermissionEnums.READ_WRITE.getCode();
    /** 管理：删除知识库、移交属主、成员授权 */
    public static final int ACT_MANAGE = PermissionEnums.ALL.getCode();

    @Autowired
    private KnowledgeBaseDomainService knowledgeBaseDomainService;

    @Autowired
    private UserClient userClient;

    /**
     * 计算当前主体对目标知识库的有效权限。
     *
     * @return 0/1/2/3
     */
    public int effectivePermission(Long kbId) {
        if (kbId == null) {
            throw new ApplicationException(ErrCodeEnum.KB_ID_PARAM_ERROR);
        }
        // fail-closed：拿不到主体就没有"授权"可言，直接 0；不允许把空主体当成管理员
        com.gientech.ragcommon.context.user.User current =
                com.gientech.ragcommon.context.user.UserContext.getUser();
        if (current == null || org.apache.commons.lang3.StringUtils.isBlank(current.getUserName())) {
            log.warn("R13-SEC-A1 no principal in context, treat as no permission for kbId={}", kbId);
            return PermissionEnums.NO_PERMISSION.getCode();
        }
        Integer userType = null;
        try {
            userType = userClient.getUserType();
        } catch (Exception ex) {
            // 取不到用户类型时按普通用户处理，宁可拒绝也不放行
            log.warn("getUserType failed, fallback to normal user: {}", ex.getMessage());
        }
        if (RoleTypeEnums.SUPER_ADMIN.getCode().equals(userType)) {
            return PermissionEnums.ALL.getCode();
        }
        Integer permission = knowledgeBaseDomainService.getHighestPermission(kbId);
        return permission == null ? PermissionEnums.NO_PERMISSION.getCode() : permission;
    }

    /**
     * 断言当前主体对知识库具备至少 required 级权限，不足则抛 30016（无足够权限）。
     * 目标知识库不存在时抛业务异常，避免"查不到即放过"。
     */
    public void assertCan(Long kbId, int required) {
        if (knowledgeBaseDomainService.findByKbId(kbId) == null) {
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        }
        int actual = effectivePermission(kbId);
        if (actual < required) {
            log.warn("R13-SEC-A1 deny kbId={} required={} actual={} user={}",
                    kbId, required, actual, com.gientech.ragcommon.context.user.UserContext.getUser());
            throw new ApplicationException(ErrCodeEnum.INSUFFICIENT_PERMISSIONS);
        }
    }

    public void assertRead(Long kbId) {
        assertCan(kbId, ACT_READ);
    }

    public void assertWrite(Long kbId) {
        assertCan(kbId, ACT_WRITE);
    }

    public void assertManage(Long kbId) {
        assertCan(kbId, ACT_MANAGE);
    }

    /** 仅超级管理员可执行的全局操作（如属主移交）。 */
    public void assertSuperAdmin() {
        Integer userType = userClient.getUserType();
        if (!RoleTypeEnums.SUPER_ADMIN.getCode().equals(userType)) {
            throw new ApplicationException(ErrCodeEnum.INSUFFICIENT_PERMISSIONS);
        }
    }
}
