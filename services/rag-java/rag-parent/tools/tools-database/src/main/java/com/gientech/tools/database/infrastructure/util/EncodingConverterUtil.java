package com.gientech.tools.database.infrastructure.util;

import cn.hutool.core.io.CharsetDetector;
import cn.hutool.core.io.IoUtil;
import cn.hutool.core.util.CharsetUtil;
import cn.hutool.core.util.StrUtil;

import java.io.*;
import java.nio.charset.Charset;

/**
 * 上传文件inputstream编码转化
 */
public class EncodingConverterUtil {
    /**
     * 已知原始编码，将InputStream转换为目标编码的InputStream
     * @param inputStream 原始输入流
     * @param sourceCharset 原始编码
     * @param targetCharset 目标编码，默认UTF-8
     * @return 转换编码后的InputStream
     * @throws IOException IO异常
     */
    public static InputStream convertToStream(InputStream inputStream, String sourceCharset, String targetCharset) throws IOException {
        // 目标编码默认使用UTF-8
        targetCharset = StrUtil.emptyToDefault(targetCharset, CharsetUtil.UTF_8);
        // 1. 用原始编码读取流内容为字符串
        String content = IoUtil.read(inputStream, CharsetUtil.charset(sourceCharset));
        // 2. 将字符串按目标编码转为字节数组，再包装为InputStream
        byte[] targetBytes = content.getBytes(CharsetUtil.charset(targetCharset));
        return new ByteArrayInputStream(targetBytes);
    }

    /**
     * 自动检测原始编码，转换为目标编码的InputStream
     * @param inputStream 原始输入流
     * @param targetCharset 目标编码，默认UTF-8
     * @return 转换编码后的InputStream
     * @throws IOException IO异常
     */
    public static InputStream convertToUTF8Stream(InputStream inputStream, String targetCharset) throws IOException {
        // 1. 读取流内容到字节数组（用于检测编码和复用）
        byte[] data = IoUtil.readBytes(inputStream);
        // 2. 检测原始编码
        String sourceCharset = detectCharset(data);
        // 3. 转换编码并返回InputStream
        return convertToStream(new ByteArrayInputStream(data), sourceCharset, targetCharset);
    }

    /**
     * 检测字节数组的编码
     * @param data 字节数组
     * @return 编码名称，默认UTF-8
     */
    private static String detectCharset(byte[] data) {
        ByteArrayInputStream inputStream = new ByteArrayInputStream(data);
        CharsetDetector detector = new CharsetDetector();
        Charset inputCharset = detector.detect(inputStream);
        return inputCharset != null ? inputCharset.displayName() : CharsetUtil.UTF_8;
    }

}
    