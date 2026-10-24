package com.gientech.ragindexservice.utils;

import cn.hutool.crypto.SecureUtil;
import org.junit.jupiter.api.Test;

/**
 * @author: shirleychen
 * @date 2025/9/3 14:34
 * @description
 */
public class SecureUtilTest {
    private static final String encKey = "C7OT8Ty8ghEFRZF1";


    public static void main(String[] args) {
        String desc = new String(SecureUtil.aes(encKey.getBytes()).decrypt("c170b235ed10c719aa0f3d81e97eec23"));
        System.out.println(desc);
    }
}
