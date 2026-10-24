package com.gientech.ragindexservice.infrastructure;

import org.apache.tika.Tika;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.web.multipart.MultipartFile;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;

public class MultipartFileUtils {

    public static MultipartFile convertToMultipartFile(InputStream inputStream, String fileName) throws IOException {
        ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream();
        byte[] buffer = new byte[1024];
        int bytesRead;
        while ((bytesRead = inputStream.read(buffer)) != -1)
            byteArrayOutputStream.write(buffer, 0, bytesRead);
        byte[] fileContent = byteArrayOutputStream.toByteArray();
        Tika tika = new Tika();
        String mediaType = tika.detect(fileContent);
        return new MockMultipartFile(fileName, fileName, mediaType, new ByteArrayInputStream(fileContent));
    }
}
