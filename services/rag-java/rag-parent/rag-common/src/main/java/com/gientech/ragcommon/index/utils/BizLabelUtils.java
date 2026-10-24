package com.gientech.ragcommon.index.utils;


import org.apache.commons.lang3.StringUtils;

import java.util.Arrays;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/**
 * @author chenjuan
 * @date 2025/5/25 0:10
 */
public class BizLabelUtils {

    public static String getLabel(String folderLabel, String fileLabel) {
        return Stream.of(folderLabel, fileLabel).flatMap(s -> Arrays.stream(s.split(","))).filter(StringUtils::isNotBlank).collect(Collectors.joining(","));
    }

    public static Set<String> getLabelArray(String folderLabel, String fileLabel) {
        return Stream.of(folderLabel, fileLabel).flatMap(s -> Arrays.stream(s.split(","))).filter(StringUtils::isNotBlank).collect(Collectors.toSet());
    }

    public static String getLabelByIdLabelMap(Map<Long, String> idLabelMap, Long fileId, Long folderId) {
        String fileLabel = idLabelMap.getOrDefault(fileId, "");
        String folderLabel = idLabelMap.getOrDefault(folderId, "");
        return getLabel(folderLabel, fileLabel);
    }

    public static Set<String> getLabelArrayByIdLabelMap(Map<String, String> idLabelMap, Long fileId, Long folderId) {
        String fileLabel = idLabelMap.getOrDefault("file_" + fileId, "");
        String folderLabel = idLabelMap.getOrDefault("folder_" + folderId, "");
        return getLabelArray(folderLabel, fileLabel);
    }

    public static String[] safeGetLabels(String label, String delimiter) {
        if (label == null || label.isEmpty()) {
            return new String[0];
        }
        return label.split(delimiter);
    }

    public static String getLabelFromLabels(Set<String> labels, String delimiter) {
        if (labels == null || labels.isEmpty()) {
            return "";
        }
        return labels.stream().filter(StringUtils::isNotBlank).collect(Collectors.joining(delimiter));
    }
}
