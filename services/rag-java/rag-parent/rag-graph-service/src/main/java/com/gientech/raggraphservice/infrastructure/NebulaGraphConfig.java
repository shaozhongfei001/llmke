package com.gientech.raggraphservice.infrastructure;

import com.vesoft.nebula.client.graph.SessionPool;
import com.vesoft.nebula.client.graph.SessionPoolConfig;
import com.vesoft.nebula.client.graph.data.HostAddress;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Lazy;

import java.net.ConnectException;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Configuration
@ConditionalOnProperty(name = "graph.type", havingValue = "nebula")
public class NebulaGraphConfig implements GraphConfig {
    @Value("${nebula.host}")
    private String host;

    @Value("${nebula.port}")
    private int port;

    @Value("${nebula.user}")
    private String user;

    @Value("${nebula.password}")
    private String password;

    @Value("${nebula.spaceName}")
    private String spaceName;

    @Value("${nebula.maxConnSize}")
    private int maxConnSize;

    @Value("${nebula.maxSessionSize:20}")
    private int maxSessionSize;

    @Value("${nebula.minSessionSize:10}")
    private int minSessionSize;

    // 该 Bean **没有任何注入点**（全模块无 @Resource/@Autowired 引用它或 SessionPool 类型），
    // 仅因 Spring 默认 eager 初始化，才在应用启动期去连 Nebula；而 **V1 图谱栈已退役**
    // （Nebula×3 容器已 Exited、r12-graphsvc.service 单元文件已删除、19529 已停），
    // 启动期连库必然抛 ConnectException，导致整个服务起不来。
    // 加 @Lazy 后该 Bean 永不初始化 → 启动不再连 Nebula；
    // 而 NebulaGraphTemplate 走的是 nebulaGraphConfig.getSessionPool(spaceName) 的**直接方法调用**
    // （非 @Bean 方法，@Configuration 只拦截 @Bean），不受影响，仍为运行时懒加载。
    //
    // ⚠️ 后来人注意：**不要用 @Resource / @Autowired 注入本 Bean**（`nebulaGraphSessionPool` 或 `SessionPool` 类型）。
    //    一旦注入，@Lazy 只会给你一个代理，**首次调用时**仍会抛 `ConnectException: NebulaGraph pool init failed`
    //    （因为 V1 的 Nebula 已退役），而且栈会出现在业务代码里，极难归因。
    //    需要图数据的场景请走 18094 的 `/v2/graph/*`，不要再把 graph-service 绑回 Nebula。
    @Lazy
    @Bean(name = "nebulaGraphSessionPool")
    public SessionPool getSessionPool() {
        return getSessionPool(spaceName);
    }

    /**
     * 按spaceName 创建session
     *
     * @param spaceName
     * @return
     */
    public SessionPool getSessionPool(String spaceName) {
        try {
            List<HostAddress> addresses = Arrays.asList(new HostAddress(host, port));
            SessionPoolConfig sessionPoolConfig = new SessionPoolConfig(addresses, spaceName, user, password);
            sessionPoolConfig.setMaxSessionSize(maxSessionSize);
            sessionPoolConfig.setMinSessionSize(minSessionSize);
            SessionPool sessionPool = new SessionPool(sessionPoolConfig);
            boolean initResult = sessionPool.init();
            if (!initResult) {
                throw new ConnectException("NebulaGraph pool init failed.");
            }

            return sessionPool;
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    @Override
    public Map<String, String> getPropertyTypeMapping() {
        return new HashMap<>();
    }
}
