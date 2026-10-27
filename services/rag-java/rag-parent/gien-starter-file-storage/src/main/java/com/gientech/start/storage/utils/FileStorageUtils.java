package com.gientech.start.storage.utils;

import com.gientech.start.storage.exception.FileStorageException;
import com.gientech.start.storage.model.FileInfo;
import com.gientech.start.storage.properties.Properties;
import com.gientech.start.storage.properties.StorageProperties;
import io.minio.BucketExistsArgs;
import io.minio.GetObjectArgs;
import io.minio.MakeBucketArgs;
import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import io.minio.StatObjectArgs;
import io.minio.ListObjectsArgs;
import io.minio.Result;
import io.minio.messages.Item;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.multipart.MultipartFile;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;

/**
 * R12 兼容实现：等价替代内网 gien-starter-file-storage 的 FileStorageUtils（MinIO 后端）。
 * 语义约定：
 *  - folder 为桶内相对前缀（可带或不带尾部斜杠）
 *  - filePath 统一返回 endPoint/bucket/objectName 形式（调用方大量依赖该拼接规则）
 * 见 docs/r12/ADAPTATIONS.md#A-02。
 */
public class FileStorageUtils {

    private static final Logger log = LoggerFactory.getLogger(FileStorageUtils.class);

    private final MinioClient minioClient;
    private final StorageProperties storageProperties;

    public FileStorageUtils(MinioClient minioClient, StorageProperties storageProperties) {
        this.minioClient = minioClient;
        this.storageProperties = storageProperties;
    }

    private Properties props(String platform) {
        return storageProperties.getByPlatform(platform == null ? storageProperties.getDefaultPlatform() : platform);
    }

    private static String normalizeFolder(String folder) {
        if (folder == null) {
            return "";
        }
        String f = folder.replace('\\', '/');
        while (f.startsWith("/")) {
            f = f.substring(1);
        }
        if (!f.isEmpty() && !f.endsWith("/")) {
            f = f + "/";
        }
        return f;
    }

    private static String trimEndPoint(String endPoint) {
        if (endPoint == null) {
            return "";
        }
        return endPoint.endsWith("/") ? endPoint.substring(0, endPoint.length() - 1) : endPoint;
    }

    private void ensureBucket(Properties p) {
        try {
            boolean exists = minioClient.bucketExists(BucketExistsArgs.builder().bucket(p.getBucketName()).build());
            if (!exists) {
                minioClient.makeBucket(MakeBucketArgs.builder().bucket(p.getBucketName()).build());
                log.info("created bucket {}", p.getBucketName());
            }
        } catch (Exception e) {
            throw new FileStorageException("bucket check/create failed: " + p.getBucketName(), e);
        }
    }

    public FileInfo putObject(String folder, MultipartFile file, String platform) {
        return putObject(folder, file, file == null ? null : file.getOriginalFilename(), platform);
    }

    public FileInfo putObject(String folder, MultipartFile file, String objectName, String platform) {
        if (file == null) {
            throw new FileStorageException("file is null");
        }
        Properties p = props(platform);
        ensureBucket(p);
        String name = objectName == null || objectName.isEmpty() ? file.getOriginalFilename() : objectName;
        String key = normalizeFolder(folder) + name;
        try (InputStream in = file.getInputStream()) {
            minioClient.putObject(PutObjectArgs.builder()
                    .bucket(p.getBucketName())
                    .object(key)
                    .stream(in, file.getSize(), -1)
                    .contentType(file.getContentType() == null ? "application/octet-stream" : file.getContentType())
                    .build());
        } catch (Exception e) {
            throw new FileStorageException("putObject failed: " + key, e);
        }
        FileInfo info = new FileInfo();
        info.setObjectName(key);
        info.setFileName(name);
        info.setBucketName(p.getBucketName());
        info.setFileSize((double) file.getSize());
        info.setContentType(file.getContentType());
        info.setFilePath(trimEndPoint(p.getEndPoint()) + "/" + p.getBucketName() + "/" + key);
        return info;
    }

    public List<FileInfo> putObjects(String folder, MultipartFile[] files, String platform) {
        List<FileInfo> list = new ArrayList<>();
        if (files == null) {
            return list;
        }
        for (MultipartFile f : files) {
            list.add(putObject(folder, f, platform));
        }
        return list;
    }

    /** 把 endPoint/bucket/object 或 bucket/object 或 object 统一解析为桶内对象名。 */
    public String getObjectNameFromUrl(String url) {
        if (url == null) {
            return null;
        }
        Properties p = props(storageProperties.getDefaultPlatform());
        String u = url;
        String endPoint = trimEndPoint(p.getEndPoint());
        if (!endPoint.isEmpty() && u.startsWith(endPoint)) {
            u = u.substring(endPoint.length());
        }
        while (u.startsWith("/")) {
            u = u.substring(1);
        }
        // R14-C-FIX-07：前端/聊天库历史写法会带网关代理前缀 /minio/（R13 撤匿名读后该前缀已不可用，
        // 但库里与 @gientech/modual 仍会拼它）。此处统一剥掉，让 stream / previewStream / markdown
        // 三条链路都能吃三种历史写法：/minio/<bucket>/...、http://host/<bucket>/...、<bucket>/...。
        if (p.getBucketName() != null) {
            while (u.startsWith("minio/" + p.getBucketName() + "/")) {
                u = u.substring("minio/".length());
            }
        }
        if (p.getBucketName() != null) {
            // 历史脏数据里桶名可能被拼两次（r12-rag/r12-rag/...），一并收敛
            while (u.startsWith(p.getBucketName() + "/")) {
                u = u.substring(p.getBucketName().length() + 1);
            }
        }
        return u;
    }

    public InputStream getInputStreamByUrl(String url, String platform) {
        Properties p = props(platform);
        String objectName = getObjectNameFromUrl(url);
        try {
            return minioClient.getObject(GetObjectArgs.builder()
                    .bucket(p.getBucketName())
                    .object(objectName)
                    .build());
        } catch (Exception e) {
            throw new FileStorageException("getInputStreamByUrl failed: " + url, e);
        }
    }

    public InputStream getInputStream(String objectName) {
        Properties p = props(storageProperties.getDefaultPlatform());
        try {
            return minioClient.getObject(GetObjectArgs.builder()
                    .bucket(p.getBucketName())
                    .object(objectName)
                    .build());
        } catch (Exception e) {
            throw new FileStorageException("getInputStream failed: " + objectName, e);
        }
    }

    public byte[] getMediaTypeByteArrayByUrl(String url, String platform) {
        try (InputStream in = getInputStreamByUrl(url, platform)) {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) > 0) {
                out.write(buf, 0, n);
            }
            return out.toByteArray();
        } catch (FileStorageException e) {
            throw e;
        } catch (Exception e) {
            throw new FileStorageException("getMediaTypeByteArrayByUrl failed: " + url, e);
        }
    }

    public boolean isExistedFile(String folder, String fileName, String platform) {
        Properties p = props(platform);
        String key = normalizeFolder(folder) + fileName;
        try {
            minioClient.statObject(StatObjectArgs.builder().bucket(p.getBucketName()).object(key).build());
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    public List<FileInfo> listFolderFiles(String folder, String platform) {
        Properties p = props(platform);
        String prefix = normalizeFolder(folder);
        List<FileInfo> list = new ArrayList<>();
        try {
            Iterable<Result<Item>> results = minioClient.listObjects(ListObjectsArgs.builder()
                    .bucket(p.getBucketName())
                    .prefix(prefix)
                    .recursive(true)
                    .build());
            for (Result<Item> r : results) {
                Item item = r.get();
                if (item.isDir()) {
                    continue;
                }
                FileInfo info = new FileInfo();
                info.setObjectName(item.objectName());
                info.setFileName(item.objectName().substring(item.objectName().lastIndexOf('/') + 1));
                info.setBucketName(p.getBucketName());
                info.setFileSize((double) item.size());
                info.setFilePath(trimEndPoint(p.getEndPoint()) + "/" + p.getBucketName() + "/" + item.objectName());
                list.add(info);
            }
        } catch (Exception e) {
            throw new FileStorageException("listFolderFiles failed: " + prefix, e);
        }
        return list;
    }
}
