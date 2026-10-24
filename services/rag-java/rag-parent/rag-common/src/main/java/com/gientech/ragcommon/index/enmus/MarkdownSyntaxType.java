package com.gientech.ragcommon.index.enmus;

/**
 * Markdown语法类型枚举
 */
public enum MarkdownSyntaxType {
    HEADER("标题"),
    UNORDERED_LIST("无序列表"),
    ORDERED_LIST("有序列表"),
    TASK_LIST("任务列表"),
    HORIZONTAL_RULE("分隔线"),
    CODE_BLOCK("代码块"),
    MATH_BLOCK("数学公式块"),
    BLOCKQUOTE("引用"),
    TABLE("表格"),
    TABLE_SEPARATOR("表格分隔符"),
    DEFINITION_LIST("定义列表"),
    FOOTNOTE("脚注"),
    REFERENCE_LINK("参考链接"),
    HTML_COMMENT("HTML注释"),
    YAML_FRONT_MATTER("YAML前置元数据"),
    INLINE_CODE("内联代码"),
    BOLD("粗体"),
    ITALIC("斜体"),
    STRIKETHROUGH("删除线"),
    LINK("链接"),
    IMAGE("图片"),
    AUTO_LINK("自动链接"),
    PLAIN_TEXT("普通文本");

    private final String description;

    MarkdownSyntaxType(String description) {
        this.description = description;
    }

    public String getDescription() {
        return description;
    }
}
