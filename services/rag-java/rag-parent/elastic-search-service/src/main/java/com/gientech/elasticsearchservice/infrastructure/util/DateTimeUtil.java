package com.gientech.elasticsearchservice.infrastructure.util;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/9/23 15:06
 */
public class DateTimeUtil {

    private static final DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    public static String getFormattedNow() {
        LocalDateTime now = LocalDateTime.now();
        return now.format(formatter);
    }
}
