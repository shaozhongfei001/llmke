package com.gientech.raggraphservice.infrastructure;

import com.vesoft.nebula.client.graph.SessionPool;
import com.vesoft.nebula.client.graph.SessionPoolConfig;
import com.vesoft.nebula.client.graph.data.HostAddress;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

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
