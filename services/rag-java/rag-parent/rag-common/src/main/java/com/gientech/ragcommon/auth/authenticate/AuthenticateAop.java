//package com.gientech.ragcommon.auth.authenticate;
//import com.gientech.ragcommon.auth.authenticate.remote.InterfaceClient;
//import com.gientech.ragcommon.global.ErrCodeEnum;
//import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
//import org.aspectj.lang.JoinPoint;
//import org.aspectj.lang.annotation.Aspect;
//import org.aspectj.lang.annotation.Before;
//import org.aspectj.lang.annotation.Pointcut;
//import org.aspectj.lang.reflect.MethodSignature;
//import org.springframework.beans.factory.annotation.Autowired;
//import org.springframework.core.annotation.Order;
//import org.springframework.http.server.PathContainer;
//import org.springframework.stereotype.Component;
//import org.springframework.web.util.pattern.PathPattern;
//import org.springframework.web.util.pattern.PathPatternParser;
//
//import java.lang.reflect.Method;
//import java.util.HashSet;
//import java.util.Objects;
//import java.util.Set;
//
//
//@Aspect
//@Component
//@Order(2)
//public class AuthenticateAop {
//
//    @Pointcut(value = "(@within(org.springframework.web.bind.annotation.RestController) " +
//            "   || @within(org.springframework.stereotype.Controller))")
//    public void pointcut() {
//    }
//
//    @Before("pointcut()")
//    public Object doAround(JoinPoint point) throws Throwable {
//        MethodSignature signature = (MethodSignature) point.getSignature();
//        Method method = signature.getMethod();
//        System.out.println(method.getName());
//        int i = 1;
//        if (1 == i)
//            throw new ApplicationException(ErrCodeEnum.INSUFFICIENT_PERMISSIONS);
//        return null;
//    }
//
//    public static void main(String[] args) {
//
//        System.out.println("======={*pathVariable}语法======");
//        PathPattern pattern = PathPatternParser.defaultInstance.parse("/article/{id}/complete");
//
//        // 提取匹配到的的变量值
//        System.out.println("是否匹配：" + pattern.matches(PathContainer.parsePath("/article1/aa/complete")));
//        System.out.println("是否匹配：" + pattern.matches(PathContainer.parsePath("/article/10/complete")));
//
////        String source = "/article/{id}/complete";
////
////        Set<String> sources = new HashSet<>();
////        sources.add("/article/{id}/complete");
////        sources.add("/article/id/complete");
////
////        String target = "/article/id/complete";
////        System.out.println(isSame(source, target));
//
//    }
//
//    public static boolean isSame(String source, String target) {
//
//        if (source.contains("{") && !source.contains("}")) {
//            return source.equals(target);
//        } else {
//            String[] s1 = source.split("/");
//            String[] s2 = target.split("/");
//            if (Objects.isNull(s1) || Objects.isNull(s2) || s1.length != s2.length)
//                return false;
//            for (int i = 0; i < s1.length; i++) {
//                if (s1[i].contains("{") && s1[i].contains("}"))
//                    continue;
//                else if (!s1[i].equals(s2[i]))
//                    return false;
//            }
//        }
//        return true;
//    }
//
//}
