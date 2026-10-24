package com.gientech.ragindexservice.infrastructure;

import java.util.regex.Pattern;

public class UrlKeywordChecker {
    // 定义包含URL相关关键字的正则表达式
    // 不区分大小写
//    private static final Pattern URL_KEYWORD_PATTERN =
//            Pattern.compile("(http|https|ftp|ftps|sftp|ssh|ws|wss|www|ww2|ww3|web|host|server|domain|dom|dns|url|uri|urn|link|href|#|/|\\\\)",
//                    Pattern.CASE_INSENSITIVE);

    private static final Pattern URL_KEYWORD_PATTERN =
            Pattern.compile("(http://|https://|ws://|wss://|ftp://|ftps://|www://|ww2://|ww3://|#|/|\\\\)",
                    Pattern.CASE_INSENSITIVE);

    /**
     * 检查文件名是否包含URL相关关键字
     * @param fileName 要检查的文件名
     * @return 如果包含URL关键字返回true，否则返回false
     */
    public static boolean containsUrlKeywords(String fileName) {
        if (fileName == null || fileName.isEmpty()) {
            return false;
        }
        return URL_KEYWORD_PATTERN.matcher(fileName).find();
    }
}
