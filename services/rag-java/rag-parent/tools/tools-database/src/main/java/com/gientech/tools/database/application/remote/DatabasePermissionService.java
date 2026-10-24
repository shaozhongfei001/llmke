package com.gientech.tools.database.application.remote;

import cn.hutool.json.JSONUtil;
import com.gientech.ragcommon.auth.dto.PrivilegeDTO;
import com.gientech.ragcommon.auth.enums.BizTypeEnums;
import com.gientech.ragcommon.auth.enums.RoleTypeEnums;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.index.enmus.PermissionEnums;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Lazy;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * 数据库权限相关
 */
@Service
public class DatabasePermissionService {
    private Logger logger = LoggerFactory.getLogger(this.getClass());
    @Autowired
    private AuthUserClient authUserClient;
    @Autowired
    private AuthPrivilegeClient authPrivilegeClient;

    /**
     * 获取数据的操作权限
     * @param databaseId
     * @return
     */
    public Integer queryDatabasePermission(Long databaseId){
        User user = UserContext.getUser();
        String userName = user.getUserName();
        logger.info("权限验证-当前用户：{}", JSONUtil.toJsonStr(userName));

        if(userName==null||"".equals(userName)){
            return null;
        }
        // 超级管理员，可管理权限
        Integer userType = authUserClient.getUserType();
        logger.info("权限验证-当前用户角色类型：{}", userType);

        if (userType!=null&&RoleTypeEnums.SUPER_ADMIN.getCode().equals(userType)) {
            return PermissionEnums.ALL.getCode();
        }

        List<PrivilegeDTO> permission = authPrivilegeClient.getPermissionByTargetId(BizTypeEnums.DATABASE.getCode(), new Long[]{databaseId});
        if(permission==null||permission.size()==0){
            return PermissionEnums.NO_PERMISSION.getCode();
        }

        return permission.get(0).getPermission();
    }
}
