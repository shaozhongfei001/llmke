package com.gientech.tools.database.infrastructure.util;

import com.gientech.ragcommon.infrastructure.exception.ApplicationException;

import java.io.InputStream;
import java.io.PushbackInputStream;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

/**
 * @author: shirleychen
 * @date 2025/9/9 17:36
 * @description
 */
public class DataTableFileTypeChecker {
    private static final byte[] XLS_MAGIC = {(byte) 0xD0, (byte) 0xCF, 0x11, (byte) 0xE0,
            (byte) 0xA1, (byte) 0xB1, 0x1A, (byte) 0xE1};
    private static final byte[] ZIP_MAGIC = {0x50, 0x4B, 0x03, 0x04};

    public static String detectExcelType(InputStream inputStream) throws Exception {

        PushbackInputStream in = new PushbackInputStream(inputStream, 1024);
        byte[] head = in.readNBytes(1024);
        in.unread(head, 0, head.length);

        // 1. xls
        if (head.length >= 8 && Arrays.equals(Arrays.copyOf(head, 8), XLS_MAGIC)) {
            return "xls";
        }
        // 2. xlsx
        if (head.length >= 4 && Arrays.equals(Arrays.copyOf(head, 4), ZIP_MAGIC)) {
            return "xlsx";
        }
        // 3. csv (启发式)
        String sample = new String(head, 0, Math.min(head.length, 512), StandardCharsets.UTF_8);
        if (looksLikeCsv(sample)) {
            //检测编码是否是utf8或者gbk
//            if (isUtf8(head, 1024) || isGbk(head,1024)) {
//                return "csv";
//            }
//            throw new ApplicationException("csv 文件编码错误！请重新上传");
            return "csv";
        }
        return "unknown";
    }

    public static boolean isGbk(byte[] data, int len) {
        int i = 0;
        while (i < len) {
            int b = data[i] & 0xFF;
            if (b <= 0x7F) {
                // 单字节 ASCII
                i++;
            } else {
                // 必须是双字节
                if (i + 1 >= len) return false;
                int b2 = data[i + 1] & 0xFF;
                // GBK 双字节范围：第1字节 0x81–0xFE，第2字节 0x40–0xFE 且 != 0x7F
                if (b >= 0x81 && b <= 0xFE && b2 >= 0x40 && b2 <= 0xFE && b2 != 0x7F) {
                    i += 2;
                } else {
                    return false;
                }
            }
        }
        return true;
    }

    // 判断字节流是否是合法 UTF-8
    private static boolean isUtf8(byte[] buf, int len) {
        int i = 0;
        while (i < len) {
            byte b = buf[i];
            if ((b & 0x80) == 0) { // 单字节 0xxxxxxx
                i++;
                continue;
            }
            int count;
            if ((b & 0xE0) == 0xC0) {
                count = 2;
            } else if ((b & 0xF0) == 0xE0) {
                count = 3;
            } else if ((b & 0xF8) == 0xF0) {
                count = 4;
            } else {
                return false;
            }
            if (i + count > len) return false;
            for (int j = 1; j < count; j++) {
                if ((buf[i + j] & 0xC0) != 0x80) {
                    return false;
                }
            }
            i += count;
        }
        return true;
    }

    private static boolean looksLikeCsv(String text) {
        // 至少包含一行
        if (!text.contains("\n")) return false;
        String firstLine = text.split("\n", 2)[0];
        // 含有分隔符
        if (firstLine.contains(",") || firstLine.contains(";") || firstLine.contains("\t")) {
            // 检查是不是可打印字符组成
            for (char c : firstLine.toCharArray()) {
                if (c < 0x20 && c != '\t' && c != '\r') {
                    return false;
                }
            }
            return true;
        }
        return false;
    }
}
