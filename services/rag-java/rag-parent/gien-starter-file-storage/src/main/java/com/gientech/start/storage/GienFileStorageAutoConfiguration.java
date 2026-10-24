package com.gientech.start.storage;

import com.gientech.start.storage.properties.StorageProperties;
import com.gientech.start.storage.utils.FileStorageUtils;
import io.minio.MinioClient;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.util.StringUtils;

/** R12 兼容自动装配：MinIO 客户端与文件存储工具。 */
@AutoConfiguration
@EnableConfigurationProperties(StorageProperties.class)
public class GienFileStorageAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean(MinioClient.class)
    public MinioClient minioClient(StorageProperties storageProperties) {
        com.gientech.start.storage.properties.Properties p = storageProperties.getDefaultStorageProperties();
        if (p == null || !StringUtils.hasText(p.getEndPoint())) {
            throw new IllegalStateException("storage.default-storage-properties.end-point 未配置，无法初始化 MinIO 客户端");
        }
        return MinioClient.builder()
                .endpoint(p.getEndPoint())
                .credentials(p.getAccessKey(), p.getSecretKey())
                .build();
    }

    @Bean
    @ConditionalOnMissingBean(FileStorageUtils.class)
    public FileStorageUtils fileStorageUtils(MinioClient minioClient, StorageProperties storageProperties) {
        return new FileStorageUtils(minioClient, storageProperties);
    }
}
