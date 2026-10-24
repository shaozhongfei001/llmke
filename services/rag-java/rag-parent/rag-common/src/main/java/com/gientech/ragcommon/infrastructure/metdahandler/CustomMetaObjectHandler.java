package com.gientech.ragcommon.infrastructure.metdahandler;

import com.baomidou.mybatisplus.core.handlers.MetaObjectHandler;
import com.gientech.ragcommon.context.user.UserContext;
import org.apache.ibatis.reflection.MetaObject;
import org.springframework.stereotype.Component;

import java.util.Date;

/**
 * @Desc MP自动填充
 * @Author ZhenPanHong
 * @Date 2025/3/5 13:35
 */
@Component
public class CustomMetaObjectHandler implements MetaObjectHandler {

    @Override
    public void insertFill(MetaObject metaObject) {
        // 自动填充创建人和创建时间
        this.strictInsertFill(metaObject, "createBy", String.class, getCurrentUser());
        this.strictInsertFill(metaObject, "gmtCreate", Date.class, new Date());
        // 自动填充更新人和更新时间
        this.strictInsertFill(metaObject, "updateBy", String.class, getCurrentUser());
        this.strictInsertFill(metaObject, "gmtModified", Date.class, new Date());
        // 自动填充逻辑删除
        this.strictInsertFill(metaObject, "isDtl", String.class, "0");
    }

    @Override
    public void updateFill(MetaObject metaObject) {
        // 自动填充更新人和更新时间
        this.strictUpdateFill(metaObject, "updateBy", String.class, getCurrentUser());
        this.strictUpdateFill(metaObject, "gmtModified", Date.class, new Date());
    }

    private String getCurrentUser() {
        return UserContext.getUser().getUserName();
    }
}