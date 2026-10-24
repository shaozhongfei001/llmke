package com.gientech.ragcommon.infrastructure.utils;

import com.gientech.ragcommon.index.enmus.MarkdownSyntaxType;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;

import java.util.regex.Pattern;

/**
 * @author chenjuan
 * @date 2025/4/28 17:26
 */
@Slf4j
public class MarkdownUtils {
    public static String cleanString(String str) {
        if (StringUtils.isEmpty(str)) {
            return "";
        }

        // 去掉<think>...</think>标签及其内容
        if (str.contains("</think>")) {
            str = str.substring(str.lastIndexOf("</think>") + 8);
        }

        // 去掉[retrieve_tag ...]...[/retrieve_tag]标签及其内容
        String start = "[retrive-tag";
        String end = "retrive-tag]";
        // 转义开头和结尾中的特殊字符
        String escapedStart = Pattern.quote(start);
        String escapedEnd = Pattern.quote(end);
        String regex = escapedStart + "(.*?)" + escapedEnd;
        str = str.replaceAll(regex, "");

        // 去Markdown格式
        str = str.replaceAll("(\\*\\*|__)(.*?)\\1", "$2");
        str = str.replaceAll("(\\*|_)(.*?)\\1", "$2");
        str = str.replaceAll("`([^`]*)`", "$1");
        str = str.replaceAll("\\[(.*?)\\]\\((.*?)\\)", "$1");
        str = str.replaceAll("!\\[(.*?)\\]\\((.*?)\\)", "$1");
        str = str.replaceAll("(?m)^#{1,6}\\s*", "");
        str = str.replaceAll("(?m)^>\\s*", "");
        str = str.replaceAll("(?m)^\\s*[-\\*]\\s+", "");
        str = str.replaceAll("(?m)^\\s*\\d+\\.\\s+", "");

        return str.trim();
    }

    public static boolean checkContentValid(String content) {
        return content.matches("#{1,6} .*") ||
                content.matches("\\* .*") ||
                content.matches("[-]{3,}$") ||
                content.matches("`{3,}.*") ||
                content.matches("> .*");
    }



    /**
     * Markdown语法匹配器
     * 提供完整的Markdown语法识别和匹配功能
     */
    public static class MarkdownSyntaxMatcher {

        // 预编译的正则表达式模式，提高性能
        private static final Pattern HEADER_PATTERN = Pattern.compile("^#{1,6}\\s+.*");
        private static final Pattern UNORDERED_LIST_PATTERN = Pattern.compile("^\\s*[\\*\\-\\+]\\s+.*");
        private static final Pattern ORDERED_LIST_PATTERN = Pattern.compile("^\\s*\\d+\\.\\s+.*");
        private static final Pattern HORIZONTAL_RULE_PATTERN = Pattern.compile("^\\s*[-*_]{3,}\\s*$");
        private static final Pattern CODE_BLOCK_PATTERN = Pattern.compile("^```.*");
        private static final Pattern BLOCKQUOTE_PATTERN = Pattern.compile("^>\\s*.*");
        private static final Pattern TABLE_PATTERN = Pattern.compile("^\\s*\\|.*\\|\\s*$");
        private static final Pattern TABLE_SEPARATOR_PATTERN = Pattern.compile("^\\s*\\|?\\s*:?-+:?\\s*(\\|\\s*:?-+:?\\s*)*\\|?\\s*$");
        private static final Pattern TASK_LIST_PATTERN = Pattern.compile("^\\s*[-*+]\\s+\\[[ xX]\\]\\s+.*");
        private static final Pattern DEFINITION_LIST_PATTERN = Pattern.compile("^\\s*:\\s+.*");
        private static final Pattern FOOTNOTE_PATTERN = Pattern.compile("^\\[\\^[^\\]]+\\]:\\s+.*");
        private static final Pattern REFERENCE_LINK_PATTERN = Pattern.compile("^\\[[^\\]]*\\]:\\s+.*");
        private static final Pattern HTML_COMMENT_PATTERN = Pattern.compile("^\\s*<!--.*-->\\s*$");
        private static final Pattern YAML_FRONT_MATTER_PATTERN = Pattern.compile("^---\\s*$");
        private static final Pattern MATH_BLOCK_PATTERN = Pattern.compile("^\\$\\$.*");

        // 内联语法模式
        private static final Pattern INLINE_CODE_PATTERN = Pattern.compile(".*`[^`]+`.*");
        private static final Pattern BOLD_PATTERN = Pattern.compile(".*(\\*\\*[^*]+\\*\\*|__[^_]+__).*");
        private static final Pattern ITALIC_PATTERN = Pattern.compile(".*(\\*[^*]+\\*|_[^_]+_).*");
        private static final Pattern STRIKETHROUGH_PATTERN = Pattern.compile(".*~~[^~]+~~.*");
        private static final Pattern LINK_PATTERN = Pattern.compile(".*\\[[^\\]]*\\]\\([^)]*\\).*");
        private static final Pattern IMAGE_PATTERN = Pattern.compile(".*!\\[[^\\]]*\\]\\([^)]*\\).*");
        private static final Pattern AUTO_LINK_PATTERN = Pattern.compile(".*<https?://[^>]+>.*");



        /**
         * 检查内容是否匹配任何Markdown语法
         * @param content 要检查的内容
         * @return 是否为Markdown语法
         */
        public static boolean isMarkdownSyntax(String content) {
            if (content == null || content.trim().isEmpty()) {
                return false;
            }

            return content.matches("^#{1,6}\\s+.*") ||           // 标题
                    content.matches("^\\s*[\\*\\-\\+]\\s+.*") ||  // 无序列表
                    content.matches("^\\s*\\d+\\.\\s+.*") ||      // 有序列表
                    content.matches("^\\s*[-*_]{3,}\\s*$") ||     // 分隔线
                    content.matches("^```.*") ||                  // 代码块开始
                    content.matches("^>\\s*.*") ||                // 引用
                    content.matches("^\\s*\\|.*\\|\\s*$") ||      // 表格行
                    content.matches("^\\s*[-*+]\\s+\\[[ xX]\\]\\s+.*") || // 任务列表
                    content.matches("^\\s*:\\s+.*") ||            // 定义列表
                    content.matches("^\\[\\^[^\\]]+\\]:\\s+.*") || // 脚注
                    content.matches("^\\[[^\\]]*\\]:\\s+.*") ||   // 参考链接
                    content.matches("^\\$\\$.*") ||               // 数学公式块
                    content.matches("^---\\s*$") ||               // YAML前置元数据
                    content.matches("^\\s*<!--.*-->\\s*$");       // HTML注释
        }

        /**
         * 获取内容的Markdown语法类型
         * @param content 要分析的内容
         * @return Markdown语法类型
         */
        public static MarkdownSyntaxType getMarkdownSyntaxType(String content) {
            if (content == null || content.trim().isEmpty()) {
                return MarkdownSyntaxType.PLAIN_TEXT;
            }

            String trimmed = content.trim();

            // 块级语法检查（按优先级排序）
            if (YAML_FRONT_MATTER_PATTERN.matcher(trimmed).matches()) {
                return MarkdownSyntaxType.YAML_FRONT_MATTER;
            }
            if (HTML_COMMENT_PATTERN.matcher(content).matches()) {
                return MarkdownSyntaxType.HTML_COMMENT;
            }
            if (HEADER_PATTERN.matcher(content).matches()) {
                return MarkdownSyntaxType.HEADER;
            }
            if (CODE_BLOCK_PATTERN.matcher(content).matches()) {
                return MarkdownSyntaxType.CODE_BLOCK;
            }
            if (MATH_BLOCK_PATTERN.matcher(content).matches()) {
                return MarkdownSyntaxType.MATH_BLOCK;
            }
            if (HORIZONTAL_RULE_PATTERN.matcher(content).matches()) {
                return MarkdownSyntaxType.HORIZONTAL_RULE;
            }
            if (TABLE_SEPARATOR_PATTERN.matcher(content).matches()) {
                return MarkdownSyntaxType.TABLE_SEPARATOR;
            }
            if (TABLE_PATTERN.matcher(content).matches()) {
                return MarkdownSyntaxType.TABLE;
            }
            if (TASK_LIST_PATTERN.matcher(content).matches()) {
                return MarkdownSyntaxType.TASK_LIST;
            }
            if (ORDERED_LIST_PATTERN.matcher(content).matches()) {
                return MarkdownSyntaxType.ORDERED_LIST;
            }
            if (UNORDERED_LIST_PATTERN.matcher(content).matches()) {
                return MarkdownSyntaxType.UNORDERED_LIST;
            }
            if (BLOCKQUOTE_PATTERN.matcher(content).matches()) {
                return MarkdownSyntaxType.BLOCKQUOTE;
            }
            if (DEFINITION_LIST_PATTERN.matcher(content).matches()) {
                return MarkdownSyntaxType.DEFINITION_LIST;
            }
            if (FOOTNOTE_PATTERN.matcher(content).matches()) {
                return MarkdownSyntaxType.FOOTNOTE;
            }
            if (REFERENCE_LINK_PATTERN.matcher(content).matches()) {
                return MarkdownSyntaxType.REFERENCE_LINK;
            }

            // 内联语法检查
            if (IMAGE_PATTERN.matcher(content).matches()) {
                return MarkdownSyntaxType.IMAGE;
            }
            if (LINK_PATTERN.matcher(content).matches()) {
                return MarkdownSyntaxType.LINK;
            }
            if (AUTO_LINK_PATTERN.matcher(content).matches()) {
                return MarkdownSyntaxType.AUTO_LINK;
            }
            if (INLINE_CODE_PATTERN.matcher(content).matches()) {
                return MarkdownSyntaxType.INLINE_CODE;
            }
            if (BOLD_PATTERN.matcher(content).matches()) {
                return MarkdownSyntaxType.BOLD;
            }
            if (ITALIC_PATTERN.matcher(content).matches()) {
                return MarkdownSyntaxType.ITALIC;
            }
            if (STRIKETHROUGH_PATTERN.matcher(content).matches()) {
                return MarkdownSyntaxType.STRIKETHROUGH;
            }

            return MarkdownSyntaxType.PLAIN_TEXT;
        }

        /**
         * 检查是否为标题行
         * @param content 内容
         * @return 是否为标题
         */
        public static boolean isHeader(String content) {
            return HEADER_PATTERN.matcher(content).matches();
        }

        /**
         * 获取标题级别
         * @param content 标题内容
         * @return 标题级别 (1-6)，非标题返回0
         */
        public static int getHeaderLevel(String content) {
            if (!isHeader(content)) {
                return 0;
            }

            int level = 0;
            for (char c : content.toCharArray()) {
                if (c == '#') {
                    level++;
                } else if (c == ' ') {
                    break;
                }
            }
            return Math.min(level, 6);
        }

        /**
         * 检查是否为列表项
         * @param content 内容
         * @return 是否为列表项
         */
        public static boolean isList(String content) {
            return UNORDERED_LIST_PATTERN.matcher(content).matches() ||
                    ORDERED_LIST_PATTERN.matcher(content).matches() ||
                    TASK_LIST_PATTERN.matcher(content).matches();
        }

        /**
         * 检查是否为代码块边界
         * @param content 内容
         * @return 是否为代码块边界
         */
        public static boolean isCodeBlockBoundary(String content) {
            return CODE_BLOCK_PATTERN.matcher(content).matches();
        }

        /**
         * 检查是否为表格行
         * @param content 内容
         * @return 是否为表格行
         */
        public static boolean isTableRow(String content) {
            return TABLE_PATTERN.matcher(content).matches() ||
                    TABLE_SEPARATOR_PATTERN.matcher(content).matches();
        }

        /**
         * 综合的Markdown语法检查
         * @param content 要检查的内容
         * @return 是否包含Markdown语法
         */
        public static boolean hasMarkdownSyntax(String content) {
            if (content == null || content.trim().isEmpty()) {
                return false;
            }

            return content.matches("^#{1,6}\\s+.*") ||           // 标题
                    content.matches("^\\s*\\*\\s+.*") ||          // 无序列表
                    content.matches("^\\s*[-]{3,}\\s*$") ||       // 分隔线
                    content.matches("^`{3,}.*") ||                // 代码块
                    content.matches("^>\\s*.*") ||                // 引用

                    // 补充的Markdown语法
                    content.matches("^\\s*\\d+\\.\\s+.*") ||      // 有序列表
                    content.matches("^\\s*[-+]\\s+.*") ||         // 其他无序列表标记
                    content.matches("^\\s*\\|.*\\|\\s*$") ||      // 表格
                    content.matches("^\\s*[-*+]\\s+\\[[ xX]\\]\\s+.*") || // 任务列表
                    content.matches("^\\[\\^[^\\]]+\\]:\\s+.*") || // 脚注
                    content.matches("^\\[[^\\]]*\\]:\\s+.*") ||   // 参考链接定义
                    content.matches("^\\$\\$.*") ||               // 数学公式块
                    content.matches("^---\\s*$") ||               // YAML前置元数据分隔符

                    // 内联语法检查
                    content.contains("`") ||                      // 内联代码
                    content.contains("**") ||                     // 粗体
                    content.contains("__") ||                     // 粗体（下划线）
                    content.contains("~~") ||                     // 删除线
                    content.matches(".*\\[[^\\]]*\\]\\([^)]*\\).*") || // 链接
                    content.matches(".*!\\[[^\\]]*\\]\\([^)]*\\).*");  // 图片
        }
    }
}
