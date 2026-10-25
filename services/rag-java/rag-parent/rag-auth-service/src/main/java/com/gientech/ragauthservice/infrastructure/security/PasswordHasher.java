package com.gientech.ragauthservice.infrastructure.security;

import cn.hutool.crypto.digest.BCrypt;

import java.math.BigInteger;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.regex.Pattern;

/**
 * R13-SEC-A3：口令安全哈希。
 * <p>
 * 历史实现是把 AES 解密后的明文直接 MD5（{@code new BigInteger(1, md5).toString(16)}，无盐、无迭代），
 * 库内一旦泄露即可被彩虹表还原。本类改为 BCrypt（自适应代价 10），并支持旧口令透明迁移：
 * <ol>
 *     <li>校验时识别 BCrypt 格式（$2a$/$2b$/$2y$）→ 直接 BCrypt 校验；</li>
 *     <li>识别旧 MD5 十六进制串（长度 &lt;= 32 的 [0-9a-f]）→ 用旧算法比对，`matches` 返回 true 后由调用方触发升级
 *         （见 {@code UserInfoDomainServiceImpl#login}），下次登录即写成 BCrypt；</li>
 *     <li>其他格式一律视为校验失败，不做"宽松匹配"。</li>
 * </ol>
 */
public final class PasswordHasher {

    private static final Pattern BCRYPT = Pattern.compile("^\\$2[aby]?\\$\\d{2}\\$[./A-Za-z0-9]{53}$");
    private static final Pattern LEGACY_MD5 = Pattern.compile("^[0-9a-f]{1,32}$");
    private static final int COST = 10;

    private PasswordHasher() {
    }

    /** 生成 BCrypt 哈希（含随机盐）。 */
    public static String encode(String rawPassword) {
        if (rawPassword == null) {
            throw new IllegalArgumentException("password must not be null");
        }
        return BCrypt.hashpw(rawPassword, BCrypt.gensalt(COST));
    }

    /**
     * 与 {@link #encode(String)} 等价，仅为了让历史调用点（try/catch {@code NoSuchAlgorithmException}）
     * 可以最小化改造：旧实现用 MessageDigest 会抛该受检异常。
     */
    public static String encodeChecked(String rawPassword) throws java.security.NoSuchAlgorithmException {
        return encode(rawPassword);
    }

    /** 是否为 BCrypt 存储格式。 */
    public static boolean isBcrypt(String stored) {
        return stored != null && BCRYPT.matcher(stored).matches();
    }

    /** 是否为历史 MD5 存储格式。 */
    public static boolean isLegacyMd5(String stored) {
        return stored != null && LEGACY_MD5.matcher(stored).matches();
    }

    /** 是否为需要迁移的历史口令（登录成功后应重写为 BCrypt）。 */
    public static boolean needsUpgrade(String stored) {
        return isLegacyMd5(stored);
    }

    /**
     * 校验明文口令与库内存储值是否匹配（兼容历史 MD5）。
     */
    public static boolean matches(String rawPassword, String stored) {
        if (rawPassword == null || stored == null || stored.isEmpty()) {
            return false;
        }
        if (isBcrypt(stored)) {
            try {
                return BCrypt.checkpw(rawPassword, stored);
            } catch (IllegalArgumentException ex) {
                return false;
            }
        }
        if (isLegacyMd5(stored)) {
            String legacy = legacyMd5(rawPassword);
            // 历史实现用 BigInteger 去前导 0，长度可能不足 32，此处做等价比较
            return legacy.equalsIgnoreCase(stored) || trimLeadingZeros(legacy).equalsIgnoreCase(trimLeadingZeros(stored));
        }
        return false;
    }

    /** 历史 MD5 算法，仅用于旧数据校验与迁移，不要用于新口令。 */
    public static String legacyMd5(String rawPassword) {
        try {
            byte[] bytes = MessageDigest.getInstance("MD5").digest(rawPassword.getBytes());
            return new BigInteger(1, bytes).toString(16);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("MD5 not available", e);
        }
    }

    private static String trimLeadingZeros(String hex) {
        int i = 0;
        while (i < hex.length() - 1 && hex.charAt(i) == '0') {
            i++;
        }
        return hex.substring(i);
    }
}
