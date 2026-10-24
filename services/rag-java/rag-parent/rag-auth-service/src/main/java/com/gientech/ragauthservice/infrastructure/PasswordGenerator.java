package com.gientech.ragauthservice.infrastructure;

import java.security.SecureRandom;

public class PasswordGenerator {
    // 定义密码包含的字符集
    private static final String LOWER_CASE = "abcdefghijklmnopqrstuvwxyz";
    private static final String UPPER_CASE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    private static final String DIGITS = "0123456789";
    private static final String SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?";
    
    // 所有字符集的组合
    private static final String ALL_CHARACTERS = LOWER_CASE + UPPER_CASE + DIGITS + SPECIAL_CHARS;
    
    // 使用安全的随机数生成器
    private static final SecureRandom random = new SecureRandom();
    
    /**
     * 生成随机密码
     * @param length 密码长度，至少为4
     * @return 生成的密码
     */
    public static String generatePassword(int length) {
        // 确保密码长度至少为4，以容纳四种类型的字符
        if (length < 4) {
            throw new IllegalArgumentException("密码长度不能小于4");
        }
        
        StringBuilder password = new StringBuilder(length);
        
        // 确保至少包含每种类型的字符各一个
        password.append(LOWER_CASE.charAt(random.nextInt(LOWER_CASE.length())));
        password.append(UPPER_CASE.charAt(random.nextInt(UPPER_CASE.length())));
        password.append(DIGITS.charAt(random.nextInt(DIGITS.length())));
        password.append(SPECIAL_CHARS.charAt(random.nextInt(SPECIAL_CHARS.length())));
        
        // 填充剩余的字符
        for (int i = 4; i < length; i++) {
            password.append(ALL_CHARACTERS.charAt(random.nextInt(ALL_CHARACTERS.length())));
        }
        
        // 打乱密码顺序
        return shuffleString(password.toString());
    }
    
    /**
     * 打乱字符串顺序
     * @param input 要打乱的字符串
     * @return 打乱后的字符串
     */
    private static String shuffleString(String input) {
        char[] characters = input.toCharArray();
        for (int i = 0; i < characters.length; i++) {
            int randomIndex = random.nextInt(characters.length);
            // 交换字符
            char temp = characters[i];
            characters[i] = characters[randomIndex];
            characters[randomIndex] = temp;
        }
        return new String(characters);
    }
    
    public static void main(String[] args) {
        // 生成10个长度为12的密码作为示例
        for (int i = 0; i < 10; i++) {
            System.out.println(generatePassword(8));
        }
    }
}
