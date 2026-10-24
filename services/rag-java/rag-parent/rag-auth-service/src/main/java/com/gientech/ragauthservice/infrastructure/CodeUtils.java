package com.gientech.ragauthservice.infrastructure;

import com.gientech.ragcommon.infrastructure.emuns.RedisKeyEnums;
import com.gientech.ragcommon.infrastructure.utils.IPUtils;

import jakarta.servlet.http.HttpServletRequest;
import java.security.MessageDigest;

/**
 * 验证码工具类
 */
public class CodeUtils {

    /**
     * 获取缓存的key
     *
     * @param request
     * @return
     */
    public static String getCaptchaKey(HttpServletRequest request) {
        String ip = IPUtils.getIpAddr(request);
        String userAgent = request.getHeader("User-Agent");

        String key = RedisKeyEnums.CAPTCHA_PREFIX + MD5(ip + userAgent);

        return key;
    }

    /**
     * 获取注册用户时缓存的key
     *
     * @param request
     * @return
     */
    public static String getRegisterCaptchaKey(HttpServletRequest request) {
        String ip = IPUtils.getIpAddr(request);
        String userAgent = request.getHeader("User-Agent");

        String key = RedisKeyEnums.REGISTER_CAPTCHA_PREFIX + MD5(ip + userAgent);

        return key;
    }

    private static String MD5(String data) {
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            byte[] array = md.digest(data.getBytes("UTF-8"));
            StringBuilder sb = new StringBuilder();
            for (byte item : array) {
                sb.append(Integer.toHexString((item & 0xFF) | 0x100).substring(1, 3));
            }
            return sb.toString().toUpperCase();
        } catch (Exception exception) {
        }
        return null;

    }

}
