package com.gientech.ragcommon.index.constant;

import com.google.common.collect.Lists;

import java.util.Arrays;
import java.util.List;

public interface IndexConstant {

    /**
     * 图片的类型
     */
    List<String> IMAGE_TYPE_LIST = Lists.newArrayList("jpeg", "jpg", "png", "gif", "webp", "bmp", "heic", "svg", "eps", "ai", "psd", "tiff", "raw", "avif");

    String FILE_FRAGMENT_DIR = "file_fragment";

    List<String> FILE_TYPE_LIST = Arrays.asList("xlsx", "html", "xls", "csv", "jpg", "jpeg", "png", "gif", "bmp", "tiff", "tif", "svg", "heic", "webp");

    List<String> IMAGE_HTML_TYPE = Arrays.asList("html", "jpeg", "jpg", "png", "gif", "webp", "bmp", "heic", "svg", "eps", "ai", "psd", "tiff", "raw", "avif");

    List<String> TEXT_TYPE_LIST = Arrays.asList("xlsx", "xls", "csv");

    List<String> FILE_TYPE_WORD = Arrays.asList("docx");

    String DOC = "doc";

    List<String> FILE_TYPE_PPT = Arrays.asList("ppt", "pptx");

    //文件名以点开头的不处理
    String EXCLUDE_FILENAME_PREFIX = ".";

    String[] APPROVED_COMPRESSED_FILE_LIST = new String[]{"zip", "tar", "7z", "rar"};

    String[] APPROVED_NORMAL_FILE_LIST = new String[]{"ppt", "pptx", "doc", "docx", "csv", "xlsx", "xls", "pdf", "txt", "html", "jpg", "jpeg", "png", "odf", "md", "json"};


    static List<String> getCollectionNames(String kbName) {
        return List.of(kbName, "table_chunks_" + kbName, "faq_" + kbName, "table_summary_" + kbName);
    }

    static List<String> getNewCollectionNames(String collectionName) {
        return List.of(collectionName, "table_chunks_" + collectionName, "faq_" + collectionName, "table_summary_" + collectionName);
    }
}
