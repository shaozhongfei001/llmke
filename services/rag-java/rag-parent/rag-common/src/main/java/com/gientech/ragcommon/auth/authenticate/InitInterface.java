package com.gientech.ragcommon.auth.authenticate;

import com.gientech.ragcommon.auth.authenticate.remote.InterfaceClient;
import com.gientech.ragcommon.auth.request.SaveInterfaceInfoReq;
import com.google.common.collect.Lists;
import io.swagger.v3.oas.annotations.Operation;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.aop.support.AopUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.cloud.openfeign.EnableFeignClients;
import org.springframework.context.ApplicationContext;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpMethod;
import org.springframework.stereotype.Component;
import org.springframework.util.CollectionUtils;
import org.springframework.web.bind.annotation.*;

import java.lang.annotation.Annotation;
import java.lang.reflect.Method;
import java.util.List;
import java.util.Map;
import java.util.Objects;

@Slf4j
@Component
@Order(1)
@EnableFeignClients
@RefreshScope
public class InitInterface {

    @Autowired
    private ApplicationContext applicationContext;

    @Value("${server.servlet.context-path}")
    private String routePrefix;

    @Value("${spring.application.name}")
    private String serverName;

    @Autowired
    private InterfaceClient interfaceClient;

    public void init() {

        Map<String, Object> controllers = applicationContext.getBeansWithAnnotation(RestController.class);
        List<SaveInterfaceInfoReq> infoReqs = Lists.newArrayList();

        for (Map.Entry<String, Object> entry : controllers.entrySet()) {
            Object value = entry.getValue();
            Class<?> aClass = AopUtils.getTargetClass(value);
            if (!aClass.getName().contains("com.gientech"))
                continue;
            String urlPrefix = "";
            RequestMapping requestMapping = aClass.getAnnotation(RequestMapping.class);
            if (!Objects.isNull(requestMapping)) {
                String[] urlPrefixs = requestMapping.value();
                if (!Objects.isNull(urlPrefixs) && urlPrefixs.length > 0) {
                    urlPrefix = urlPrefixs[0];
                    if(urlPrefix.startsWith("/"))
                        urlPrefix = urlPrefix.substring(1);
                    if (urlPrefix.endsWith("/"))
                        urlPrefix = urlPrefix.substring(0, urlPrefix.lastIndexOf("/"));

                }

            }
            Method[] declaredMethods = aClass.getMethods();
            for (Method declaredMethod : declaredMethods) {
                //swagger的注解
                Operation operation = declaredMethod.getAnnotation(Operation.class);
                String summary = Objects.isNull(operation) ? "" : operation.summary();

                String url = "";
                String method = null;

                Annotation[] annotations = declaredMethod.getAnnotations();
                for (Annotation annotation : annotations) {
                    if (annotation instanceof PostMapping || annotation instanceof PutMapping || annotation instanceof GetMapping || annotation instanceof DeleteMapping) {
                        SaveInterfaceInfoReq saveInterfaceInfoReq = bulidInterfaceInfoReq(annotation, urlPrefix, url, method, summary);
                        infoReqs.add(saveInterfaceInfoReq);
                    }
                }
            }
        }
        //将接口数据保存到数据库中(如果接口存在,则不处理)
        if (!CollectionUtils.isEmpty(infoReqs)) {
            interfaceClient.saveBatch(infoReqs);
        }
    }

    private SaveInterfaceInfoReq bulidInterfaceInfoReq(Annotation annotation, String urlPrefix, String url, String method, String summary) {

        SaveInterfaceInfoReq saveInterfaceInfoReq = new SaveInterfaceInfoReq();
        if (annotation instanceof PostMapping) {
            PostMapping postMapping = (PostMapping) annotation;
            if (postMapping.value().length > 0)
                url = postMapping.value()[0];
            method = HttpMethod.POST.name();
        } else if (annotation instanceof GetMapping) {
            GetMapping getMapping = (GetMapping) annotation;
            if (getMapping.value().length > 0)
                url = getMapping.value()[0];
            method = HttpMethod.GET.name();
        } else if (annotation instanceof DeleteMapping) {
            DeleteMapping deleteMapping = (DeleteMapping) annotation;
            if (deleteMapping.value().length > 0)
                url = deleteMapping.value()[0];
            method = HttpMethod.DELETE.name();
        } else if (annotation instanceof PutMapping) {
            PutMapping putMapping = (PutMapping) annotation;
            if (putMapping.value().length > 0)
                url = putMapping.value()[0];
            method = HttpMethod.PUT.name();
        }

        if (StringUtils.isNotBlank(url) && url.startsWith("/"))
            url = url.substring(url.indexOf("/") + 1);

        StringBuffer urlSb = new StringBuffer(routePrefix);
        if (!StringUtils.isEmpty(urlPrefix))
            urlSb.append("/").append(urlPrefix);

        if (!StringUtils.isEmpty(url))
            urlSb.append("/").append(url);

        String uri = urlSb.toString();
        saveInterfaceInfoReq.setAppNameAbbreviate(routePrefix.replace("/",""));
        saveInterfaceInfoReq.setId(generateId(serverName, uri, method));
        saveInterfaceInfoReq.setAppName(serverName);
        saveInterfaceInfoReq.setName(summary);
        saveInterfaceInfoReq.setUrl(uri);
        saveInterfaceInfoReq.setMethod(method);
        return saveInterfaceInfoReq;
    }

    private Long generateId(String serverName, String url, String method) {
        Integer idHashCode = new StringBuffer().append(serverName).append(url).append(method).toString().hashCode();
        //处理负数
        Integer id = idHashCode & Integer.MAX_VALUE;
        return id.longValue();
    }
}
