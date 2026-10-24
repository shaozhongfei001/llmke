package com.gientech.ragcommon.index.utils;


import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonToken;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.*;

import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;

/**
 * JSON文件分页处理工具类
 * @author: shirleychen
 * @date 2025/9/1 13:09
 * @description
 */
public class JSONPagination {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    /**
     * 分页结果类
     */
    @Data
    public static class PageResult<T> {
        private String id;
        private List<T> data;
        private int currentPage;
        private int pageSize;
        private long totalCount;
        private int totalPages;

        public PageResult() {
            this.data = new ArrayList<>();
        }

        public PageResult(List<T> data, int currentPage, int pageSize, long totalCount) {
            this.data = data;
            this.currentPage = currentPage;
            this.pageSize = pageSize;
            this.totalCount = totalCount;
            this.totalPages = (int) Math.ceil((double) totalCount / pageSize);
        }

        public boolean hasNext() { return currentPage < totalPages; }
        public boolean hasPrevious() { return currentPage > 1; }

        @Override
        public String toString() {
            return String.format("Page %d/%d, Size: %d, Total: %d, Data: %d items",
                    currentPage, totalPages, pageSize, totalCount, data.size());
        }
    }

    /**
     * 方法2：流式分页 - 适用于大型JSON文件
     * 使用流式解析，不会将整个文件加载到内存
     */
    public static PageResult<JsonNode> paginateStream(InputStream inputStream, int page, int pageSize)
            throws IOException {

        List<JsonNode> pageData = new ArrayList<>();
        long totalCount = 0;
        int startIndex = (page - 1) * pageSize;
        int endIndex = startIndex + pageSize;
        int currentIndex = 0;

        try (inputStream;
             JsonParser parser = MAPPER.getFactory().createParser(inputStream)) {

            // 找到数组开始
            if (parser.nextToken() == JsonToken.START_OBJECT) {
                while (parser.nextToken() != JsonToken.END_OBJECT) {
                    String fieldName = parser.getCurrentName();
                    parser.nextToken();

                    if ("data".equals(fieldName) && parser.getCurrentToken() == JsonToken.START_ARRAY) {
                        // 遍历数组元素
                        while (parser.nextToken() == JsonToken.START_OBJECT) {
                            if (currentIndex >= startIndex && currentIndex < endIndex) {
                                JsonNode node = MAPPER.readTree(parser);
                                pageData.add(node);
                            } else {
                                parser.skipChildren();
                            }
                            currentIndex++;
                            totalCount++;
                        }
                        break;
                    } else if (parser.getCurrentToken() == JsonToken.START_ARRAY) {
                        // 直接是数组的情况
                        while (parser.nextToken() == JsonToken.START_OBJECT) {
                            if (currentIndex >= startIndex && currentIndex < endIndex) {
                                JsonNode node = MAPPER.readTree(parser);
                                pageData.add(node);
                            } else {
                                parser.skipChildren();
                            }
                            currentIndex++;
                            totalCount++;
                        }
                        break;
                    } else {
                        parser.skipChildren();
                    }
                }
            } else if (parser.getCurrentToken() == JsonToken.START_ARRAY) {
                // 直接是数组的情况
                while (parser.nextToken() == JsonToken.START_OBJECT) {
                    if (currentIndex >= startIndex && currentIndex < endIndex) {
                        JsonNode node = MAPPER.readTree(parser);
                        pageData.add(node);
                    } else {
                        parser.skipChildren();
                    }
                    currentIndex++;
                    totalCount++;
                }
            }
        }

        return new PageResult<>(pageData, page, pageSize, totalCount);
    }

    /**
     * 方法3：预处理分页 - 先统计总数，再分页读取
     * 适用于需要准确分页信息的场景
     */
    public static long countJsonArrayElements(String filePath) throws IOException {
        long count = 0;

        try (FileInputStream fis = new FileInputStream(filePath);
             JsonParser parser = MAPPER.getFactory().createParser(fis)) {

            if (parser.nextToken() == JsonToken.START_OBJECT) {
                while (parser.nextToken() != JsonToken.END_OBJECT) {
                    String fieldName = parser.getCurrentName();
                    parser.nextToken();

                    if ("data".equals(fieldName) && parser.getCurrentToken() == JsonToken.START_ARRAY) {
                        while (parser.nextToken() == JsonToken.START_OBJECT) {
                            parser.skipChildren();
                            count++;
                        }
                        break;
                    } else {
                        parser.skipChildren();
                    }
                }
            } else if (parser.getCurrentToken() == JsonToken.START_ARRAY) {
                while (parser.nextToken() == JsonToken.START_OBJECT) {
                    parser.skipChildren();
                    count++;
                }
            }
        }

        return count;
    }

    /**
     * 方法4：自定义对象分页
     * 将JSON转换为自定义对象进行分页
     */
    public static <T> PageResult<T> paginateWithClass(String filePath, int page, int pageSize, Class<T> clazz)
            throws IOException {

        List<T> pageData = new ArrayList<>();
        long totalCount = 0;
        int startIndex = (page - 1) * pageSize;
        int endIndex = startIndex + pageSize;
        int currentIndex = 0;

        try (FileInputStream fis = new FileInputStream(filePath);
             JsonParser parser = MAPPER.getFactory().createParser(fis)) {

            if (parser.nextToken() == JsonToken.START_OBJECT) {
                while (parser.nextToken() != JsonToken.END_OBJECT) {
                    String fieldName = parser.getCurrentName();
                    parser.nextToken();

                    if ("data".equals(fieldName) && parser.getCurrentToken() == JsonToken.START_ARRAY) {
                        while (parser.nextToken() == JsonToken.START_OBJECT) {
                            if (currentIndex >= startIndex && currentIndex < endIndex) {
                                T obj = MAPPER.readValue(parser, clazz);
                                pageData.add(obj);
                            } else {
                                parser.skipChildren();
                            }
                            currentIndex++;
                            totalCount++;
                        }
                        break;
                    } else {
                        parser.skipChildren();
                    }
                }
            }
        }

        return new PageResult<>(pageData, page, pageSize, totalCount);
    }

    // 测试示例
    public static void main(String[] args) {
//        try {
//            // 创建测试JSON文件
//            createTestJSONFile("test_data.json");
//
//            System.out.println("\n=== 流式分页测试 ===");
//            PageResult<JsonNode> result2 = paginateStream("test_data.json", 2, 3);
//            System.out.println(result2);
//            result2.getData().forEach(node -> System.out.println("  " + node));
//
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
    }
}


