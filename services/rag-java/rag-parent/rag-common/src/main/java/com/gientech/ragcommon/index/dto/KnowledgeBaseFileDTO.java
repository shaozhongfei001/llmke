package com.gientech.ragcommon.index.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import com.gientech.ragcommon.infrastructure.utils.PdfUtils;
import com.gitee.sunchenbin.mybatis.actable.annotation.Column;
import com.google.common.collect.Lists;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.apache.commons.lang3.StringUtils;

import java.util.Arrays;
import java.util.Date;
import java.util.List;
import java.util.Objects;

/**
 * <p>
 * 知识库明细
 * </p>
 *
 * @author wudf
 * @since 2024-06-04
 */
@NoArgsConstructor
@AllArgsConstructor
@Schema(name = "文件详情")
@Data
public class KnowledgeBaseFileDTO {

    @JsonSerialize(using = ToStringSerializer.class)
    @Schema(name = "id", description = "主键")
    private Long id;

    @Schema(name = "kbId", description = "知识库id")
    private Long kbId;

    @Schema(name = "fileName", description = "文件名称")
    private String fileName;

    @Schema(name = "fileSize", description = "文件大小 M")
    private Double fileSize;

    @Schema(name = "size", description = "文件大小 带单位")
    private String size;

    @Schema(name = "filePath", description = "文件路径")
    private String filePath;

    @Schema(name = "fullTextPath", description = "全文txt路径")
    private String fullTextPath;

    @Schema(name = "convertedFilePath", description = "更易于算法解析的文件的路径")
    private String convertedFilePath;

    @Schema(name = "status", description = "状态  0:删除 1:正常 2:解析中，3:解析成功 4: 解析失败")
    private Integer status;

    @Schema(name = "isEnable", description = "启用禁用状态 0:禁用;1启用")
    private Integer isEnable;

    @Schema(name = "uploadTime", description = "文件上传时间")
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8")
    @JsonProperty("uploadTime")
    private Date gmtCreate;

    @Schema(name = "parseType", description = "文件解析类型: 1 文件解析；2 FAQ解析 3 图解析；4 文档上传问答 ； 10 文件解析&faq抽取")
    private Integer parseType;

    @JsonProperty("count")
    @Schema(name = "aqCount", description = "问答对数")
    private Long aqCount = 0L;

    @Schema(name = "chunkSize", description = "文本块大小(块token数)")
    private Integer chunkSize = 0;

    @Schema(name = "fileType", description = "文档类型（解析方法），目前支持四种类型，[naive, laws, book, table]")
    private String fileType;

    @Schema(name = "embeddingModelName", description = "嵌入模型名称")
    private String embeddingModelName;

    @Schema(name = "parsedFilePath", description = "解析后的文件路径")
    private String parsedFilePath;

    @Schema(name = "faqExtractStatus", description = "faq抽取状态 1 未抽取；2 抽取成功 2 抽取失败 默认值 1")
    private Integer faqExtractStatus;

    //    @JsonFormat(pattern = "yyyy-MM-dd",timezone = "GMT+8")
    @Schema(name = "reviseDate", description = "修订实时间")
    private String reviseDate;

    @Schema(name = "parentFileName", description = "父文件名称")
    private String parentFileName;

    @Schema(name = "version", description = "版本号")
    private String version;

    @Schema(name = "folderId", description = "文件夹id")
    private Long folderId;

    @Schema(name = "folderName", description = "文件夹名称")
    private String folderName;

    @Schema(name = "sourceUrl", description = "文件导入url")
    private String sourceUrl;

    @Schema(name = "synLogs", description = "文件解析/抽取异常日志")
    private List<SynLogDTO> synLogs = Lists.newArrayList();

    @Schema(name = "kbFiles", description = "子文件")
    private List<KnowledgeBaseFileDTO> kbFiles;

    @Schema(name = "isFolder", description = "是否是文件夹 0:否  1:是")
    private Integer isFolder;

    @Schema(name = "imagePaths", description = "图片路径")
    private List<String> imagePaths;

    @Schema(name = "tableFilePaths", description = "表格路径")
    private String tableFilePaths;

    @Schema(name = "pdfPage", description = "pdf 文件页数")
    private Integer pdfPage;

    @Schema(name = "nodeCount", description = "节点数")
    private Integer nodeCount = 0;

    @Schema(name = "edgeCount", description = "关系数")
    private Integer edgeCount = 0;

    @Schema(name = "uid", description = "文件的uid(uid是前端生成的,文档上传问答使用,通过uid来判断文件解析状态)")
    private String uid;

    @Schema(name = "graphParseStatus", description = "图解析状态 1 未解析；2 解析中 3 解析成功 4 解析失败")
    private Integer graphParseStatus;

    @Schema(name = "上传状态--解决上传失败信息太少", description = " 1 上传成功；2 上传失败 ")
    private Integer uploadStatus;

    @Schema(name = "上传结果信息--解决上传失败信息太少")
    private String message;

    @Schema(name = "index--和公文对齐", description = "文件顺序")
    private Integer index;

    @Schema(name = "chunking", description = "是否解析切片")
    private boolean chunking;

    @Schema(name = "kbName", description = "知识库")
    private String kbName;

    @Schema(name = "elementType", description = "elementType")
    private Integer elementType;

    @Schema(name = "parentId", description = "parentId")
    private Long parentId;

    @Schema(name = "permission", description = "permission")
    private Integer permission = 3;

    @Schema(name = "fullFolderPath", description = "文件路径(文件夹+文件名)")
    private String fullFolderPath;

    @Schema(name = "fullFolderPath", description = "文件组id,算法端生成")
    private String groupId;

    @Schema(name = "label", description = "文件/文件夹标签")
    private String label;

    @Schema(name = "chunkType", description = "切片策略")
    private String chunkType;

    public KnowledgeBaseFileDTO(String fileName) {
        this.fileName = fileName;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        KnowledgeBaseFileDTO fileDTO = (KnowledgeBaseFileDTO) o;
        return Objects.equals(id, fileDTO.id) && Objects.equals(kbId, fileDTO.kbId) && Objects.equals(fileName, fileDTO.fileName) && Objects.equals(folderId, fileDTO.folderId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, kbId, fileName, folderId);
    }

    public String getSize() {
        return formatSize(fileSize);
    }

    /**
     * R14-LIVE-09：fileSize 是**字节**，原实现直接拼 "MB"，
     * 于是 29KB 的 pptx 在列表里显示成 "29388.0MB"（数字对、量级错 1024 倍）。
     * 统一按 1024 进制换算，四个档位各自带单位。
     */
    public static String formatSize(Object raw) {
        Double bytes = null;
        if (raw instanceof Number) {
            bytes = ((Number) raw).doubleValue();
        } else if (raw != null && !String.valueOf(raw).trim().isEmpty()) {
            try {
                bytes = Double.parseDouble(String.valueOf(raw).trim());
            } catch (NumberFormatException ignore) {
                return String.valueOf(raw);
            }
        }
        if (bytes == null || bytes <= 0) {
            return "0 B";
        }
        double v = bytes;
        if (v < 1024) {
            return String.format(java.util.Locale.ROOT, "%.0f B", v);
        }
        double kb = v / 1024;
        if (kb < 1024) {
            return String.format(java.util.Locale.ROOT, "%.1f KB", kb);
        }
        double mb = kb / 1024;
        if (mb < 1024) {
            return String.format(java.util.Locale.ROOT, "%.1f MB", mb);
        }
        return String.format(java.util.Locale.ROOT, "%.2f GB", mb / 1024);
    }

    @JsonIgnore
    public Long getCommonId() {
        if (Objects.nonNull(this.isFolder) && this.isFolder == 1) {
            return this.folderId;
        } else {
            return this.id;
        }
    }

    @JsonIgnore
    public String getCommonIdStr() {
        if (Objects.nonNull(this.isFolder) && this.isFolder == 1) {
            return "folder_" + this.folderId;
        } else {
            return "file_" + this.id;
        }
    }

}
