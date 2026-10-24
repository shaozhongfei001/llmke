package com.gientech.ragcommon.context.user;

import java.util.Objects;

/**
 * @author wudengfeng
 */
public class UserContext {

    private static final ThreadLocal<User> THREAD_LOCAL = new InheritableThreadLocal<>();

    public static User getUser(){
        return Objects.isNull(THREAD_LOCAL.get()) ? new User() : THREAD_LOCAL.get();
    }

    public static void setUser(User user){
        THREAD_LOCAL.set(user);
    }

    public static void removeUser(){
        THREAD_LOCAL.remove();
    }
}
