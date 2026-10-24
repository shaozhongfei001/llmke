package com.gientech.start.storage.properties;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 存储配置（R12 兼容实现）。
 * 对应 yml：
 * storage:
 *   default-platform: rag-qa
 *   default-storage-properties: {end-point, bucket-name, access-key, secret-key}
 *   storages: { rag-index: {...} }
 */
@Data
@ConfigurationProperties(prefix = "storage")
public class StorageProperties {

    private String defaultPlatform = "rag-qa";

    private Properties defaultStorageProperties = new Properties();

    private Map<String, Properties> storages = new LinkedHashMap<>();

    /** 按平台取存储配置，未命中回落到默认。 */
    public Properties getByPlatform(String platform) {
        if (platform != null && storages != null && storages.containsKey(platform)) {
            return storages.get(platform);
        }
        return defaultStorageProperties;
    }
}
