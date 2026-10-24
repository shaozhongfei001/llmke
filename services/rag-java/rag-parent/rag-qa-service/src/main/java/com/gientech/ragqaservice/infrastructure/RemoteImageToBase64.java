package com.gientech.ragqaservice.infrastructure;

import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.Resource;
import org.springframework.core.io.UrlResource;

import java.io.IOException;
import java.io.InputStream;
import java.net.MalformedURLException;
import java.net.URL;
import java.util.Base64;

@Slf4j
public class RemoteImageToBase64 {

    public static String convertRemoteImageToBase64(String imageUrl) {
        try {
            URL url = new URL(imageUrl);
            Resource resource = new UrlResource(url);
            try (InputStream inputStream = resource.getInputStream()) {
                byte[] imageBytes = inputStream.readAllBytes();
                return Base64.getEncoder().encodeToString(imageBytes);
            }
        } catch (MalformedURLException e) {
            log.error("错误的 URL 格式: " + e.getMessage());
        } catch (IOException e) {
            log.error("读取远程图片时发生 I/O 错误: " + e.getMessage());
        }
        return null;
    }

    public static void main(String[] args) {
        String  imageUrl = "http://10.15.12.13:9000/dev-rag-data/压缩包5/微信截图_20250410095250.png/V0/微信截图_20250410095250.png";
        String base64Image = convertRemoteImageToBase64(imageUrl);
        if (base64Image != null) {
            System.out.println("Base64 编码的图片: " + base64Image);
        }
    }
}    