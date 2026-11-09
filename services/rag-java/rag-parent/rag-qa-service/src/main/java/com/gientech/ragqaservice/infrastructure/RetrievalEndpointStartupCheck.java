package com.gientech.ragqaservice.infrastructure;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.URI;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 检索依赖启动自检（2026-11-07 故障复盘产出）。
 *
 * <p>背景：阶段 4 下线 19532 后，运行仓 {@code application-r12.yml} 仍把
 * {@code search-docs-url} 指向 19532，而源码仓已改成 19995。服务照常启动、端口照常监听，
 * 但每次检索都连接被拒；异常在 {@code AiServiceImpl.retrieveRecall} 被 catch 后返回 null，
 * 用户只看到「抱歉未能找到您要的答案」，运维侧没有任何启动期告警。
 *
 * <p>本类做两件事：
 * <ol>
 *   <li>启动时无条件打印所有检索依赖的<b>实际加载地址</b>，双仓漂移一眼可见；</li>
 *   <li>对每个地址做 TCP 可达性探测，不通就按 {@code fail-fast} 阻断启动（默认阻断）。</li>
 * </ol>
 *
 * <p>开关（放在运行仓配置里，便于故障时降级）：
 * <pre>
 * rag-qa.startup-check.enabled: true|false          默认 true
 * rag-qa.startup-check.fail-fast: true|false       默认 true，false 时只告警不阻断
 * rag-qa.startup-check.connect-timeout-ms: 1500    单地址探测超时
 * </pre>
 */
@Slf4j
@Component
public class RetrievalEndpointStartupCheck implements ApplicationRunner {

    private final NacosConfig nacosConfig;

    /** retrieve-url 没有被 NacosConfig 收编，这里单独读取，避免漏检。 */
    @Value("${spring.ai.gt.retrieve-url:}")
    private String retrieveUrl;

    @Value("${rag-qa.startup-check.enabled:true}")
    private boolean enabled;

    @Value("${rag-qa.startup-check.fail-fast:true}")
    private boolean failFast;

    @Value("${rag-qa.startup-check.connect-timeout-ms:1500}")
    private int connectTimeoutMs;

    @Autowired
    public RetrievalEndpointStartupCheck(NacosConfig nacosConfig) {
        this.nacosConfig = nacosConfig;
    }

    @Override
    public void run(ApplicationArguments args) {
        Map<String, String> targets = new LinkedHashMap<>();
        targets.put("spring.ai.gt.search-docs-url", nacosConfig.getSearchDocsUrl());
        targets.put("spring.ai.gt.search-docs-global-url", nacosConfig.getSearchDocsGlobalUrl());
        targets.put("spring.ai.gt.retrieve-url", retrieveUrl);
        targets.put("spring.ai.gt.llm-chat-url", nacosConfig.getLlmChatUrl());
        targets.put("spring.ai.gt.llm-url", nacosConfig.getLlmUrl());

        StringBuilder loaded = new StringBuilder("检索依赖实际加载地址（防双仓漂移）：");
        targets.forEach((k, v) -> loaded.append("\n  ").append(k).append(" = ").append(v));
        log.info(loaded.toString());

        if (!enabled) {
            log.warn("检索依赖启动自检已被 rag-qa.startup-check.enabled=false 关闭");
            return;
        }

        List<String> failures = new ArrayList<>();
        for (Map.Entry<String, String> entry : targets.entrySet()) {
            String key = entry.getKey();
            String url = entry.getValue();
            if (url == null || url.isBlank()) {
                failures.add(key + " 未配置（值为空）");
                continue;
            }
            try {
                URI uri = URI.create(url.trim());
                String host = uri.getHost();
                int port = uri.getPort() >= 0
                        ? uri.getPort()
                        : ("https".equalsIgnoreCase(uri.getScheme()) ? 443 : 80);
                if (host == null) {
                    failures.add(key + " = " + url + " 无法解析主机");
                    continue;
                }
                try (Socket socket = new Socket()) {
                    socket.connect(new InetSocketAddress(host, port), connectTimeoutMs);
                }
                log.info("检索依赖自检通过: {} -> {}:{}", key, host, port);
            } catch (IOException ex) {
                failures.add(key + " = " + url + " 不可达（"
                        + ex.getClass().getSimpleName() + ": " + ex.getMessage() + "）");
            } catch (IllegalArgumentException ex) {
                failures.add(key + " = " + url + " 不是合法 URL（" + ex.getMessage() + "）");
            }
        }

        if (failures.isEmpty()) {
            log.info("检索依赖启动自检全部通过（{} 项）", targets.size());
            return;
        }

        String message = "【检索依赖启动自检失败】以下地址不可用，智能问答会静默降级为"
                + "「找不到答案」：\n  - " + String.join("\n  - ", failures)
                + "\n请核对运行仓 platform/r12/conf/rag-qa-service/application-r12.yml"
                + " 与源码仓配置是否一致，以及对应服务是否已启动。";
        log.error(message);
        if (failFast) {
            throw new IllegalStateException(message);
        }
        log.error("rag-qa.startup-check.fail-fast=false：仅告警，服务带故障继续启动");
    }
}
