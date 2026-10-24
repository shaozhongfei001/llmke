package com.gientech.ragindexservice.infrastructure.cache;

import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
import org.springframework.stereotype.Component;

import java.util.Objects;
import java.util.concurrent.TimeUnit;

/**
 * @author chenjuan
 * @date 2025/8/4 15:47
 */
@Component
public class FileTotalPagesCache {

    public record FileKey(String path) {
        @Override
        public boolean equals(Object o) {
            if (this == o) {
                return true;
            }
            if (o == null || getClass() != o.getClass()) {
                return false;
            }
            FileKey fileKey = (FileKey) o;
            return Objects.equals(path, fileKey.path);
        }

        @Override
        public int hashCode() {
            return Objects.hashCode(path);
        }
    }

    private static final Cache<FileKey, Integer> CACHE = Caffeine.newBuilder()
            .maximumSize(1000)
            .expireAfterWrite(3, TimeUnit.HOURS)
            .build();

    public static void putBlockCount(String filePath, int count) {
        CACHE.put(new FileKey(filePath), count);
    }

    public static Integer getBlockCount(String filePath) {
        FileKey key = new FileKey(filePath);
        return CACHE.getIfPresent(key);
    }
}
