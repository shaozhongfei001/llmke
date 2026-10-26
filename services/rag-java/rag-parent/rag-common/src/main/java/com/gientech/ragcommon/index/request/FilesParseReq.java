package com.gientech.ragcommon.index.request;


import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.gientech.ragcommon.index.dto.KnowledgeBaseFileDTO;
import com.gientech.ragcommon.index.enmus.PlatFormEnums;
import com.google.common.collect.Lists;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Schema(name = "文本解析请求参数体", requiredProperties = {"files", "knowledge_base_name"})
@Data
@AllArgsConstructor
@NoArgsConstructor
public class FilesParseReq {

    @Schema(name = "folder_ids", description = "文件夹id")
    @JsonProperty("folder_ids")
    private List<Long> folderIds;

    @Schema(name = "is_all", description = "是否全部解析或抽取")
    @JsonProperty("is_all")
    private Boolean isAll = false;

    @Schema(name = "exclude_fileIds", description = "排除的文件id")
    @JsonProperty("exclude_file_ids")
    private List<Long> excludeFileIds;

    @Schema(name = "excludeFolderIds", description = "排除的文件夹id")
    @JsonProperty("exclude_folder_ids")
    private List<Long> excludeFolderIds;

    @Schema(name = "files", description = "件路径列表，和文件夹路径、文件ID列表不允许同时为空或者None")
    @JsonProperty("files")
    private List<File> files = Lists.newArrayList();

    @Schema(name = "file_ids", description = "文件ID列表，minIO中对应的文件ID，和文件路径列表、文件夹路径不能同时为空或者None")
    @JsonProperty("file_ids")
    private List<String> fileIds;

    @Schema(name = "knowledge_base_name", description = "知识库名称")
    @JsonProperty("knowledge_base_name")
    private String knowledgeBaseName;

    @Schema(name = "knowledge_base_id", description = "知识库id")
    @JsonProperty("knowledge_base_id")
    private Long knowledgeBaseId;

    @Schema(name = "override", description = "是否覆盖同名文件 默认值 ture")
    private Boolean override = true;

    @Schema(name = "chunk_size", description = "文本块大小(块token数) 默认500")
    @JsonProperty("chunk_size")
    private Integer chunkSize = 500;

    @Schema(name = "chunk_overlap", description = "文本块重叠大小 默认20")
    @JsonProperty("chunk_overlap")
    private Integer chunkOverlap = 20;

    @Schema(name = "file_type", description = "文档类型（解析方法），目前支持四种类型，[naive, laws, book, table]")
    @JsonProperty("file_type")
    private String fileType;

    @Schema(name = "embedding_model_name", description = "嵌入模型名称")
    @JsonProperty("embedding_model_name")
    private String embeddingModelName;

    @Schema(name = "extract_model_name", description = "抽取模型名称")
    @JsonProperty("extract_model_name")
    private String extractModelName;

    @JsonProperty("save_txt")
    private boolean saveTxt;

    @JsonProperty("need_chunk")
    private boolean needChunk = true;

    @Schema(name = "reParse", description = "是否需要重新解析 ture 是; false 否  默认值false")
    private Boolean reParse = Boolean.TRUE;

    @JsonIgnore
    private Boolean needAuth = true;

    @JsonIgnore
    private String innerCallUser;

    @JsonIgnore
    private String innerCallUserId;

    @Data
    public static class File {
        @Schema(name = "file_id", description = "文件id")
        @JsonProperty("file_id")
        private Long fileId;

        @Schema(name = "file_name", description = "文件名称")
        @JsonProperty("file_name")
        private String fileName;

        @Schema(name = "parseType", description = "解析类型")
        private Integer parseType;

        @Schema(name = "file_path", description = "源文件路径")
        @JsonProperty("file_path")
        private String filePath;

        @Schema(name = "converted_file_path", description = "更易于算法解析的路径")
        @JsonProperty("converted_file_path")
        private String convertedFilePath;

        @Schema(name = "file_size", description = "文件大小")
        @JsonProperty("file_size")
        private String fileSize;

        @Schema(name = "parent_file_name", description = "父文件名称")
        @JsonProperty("parent_file_name")
        private String parentFileName;

        /**
         * R13-VER-10：文件版本号（V0/V1…），随解析请求下发，落进 chunk metadata，
         * 供检索按"当前有效版本"去重与引用标注。
         */
        @JsonProperty("version")
        private String version;

        @Schema(name = "文件夹id", description = "文件夹id")
        @JsonProperty("folder_id")
        private Long folderId;

        @Schema(name = "文件标签列表", description = "文件标签")
        private String[] labels;

        public void safeSetLabels(String label, String delimiter) {
            if (label == null || label.isEmpty() || !label.contains(delimiter)) {
                this.labels = new String[0];
                return;
            }
            this.labels = label.split(delimiter);
        }
    }

    public void adjustByPlatform(String platform) {
        if (platform.equals(PlatFormEnums.INTELBRAIN_DW.getCode())) {
            this.saveTxt = true;
        }
    }

    public static String[] safeSetLabels(String label, String delimiter) {
        if (label == null || label.isEmpty() || !label.contains(delimiter)) {
            return new String[0];
        }
        return label.split(delimiter);
    }

    /**
     * {
     * "files": [
     * {
     * "folder_id": null,
     * "file_path": "dev-rag-data/测试0816/关于修订印发《中国电子信息产业集团有限公司数字化管理制度》的通知.pdf/V0/关于修订印发《中国电子信息产业集团有限公司数字化管理制度》的通知.pdf",
     * "file_size": "0.29MB",
     * "file_id": 113937,
     * "parent_file_name": "关于修订印发《中国电子信息产业集团有限公司数字化管理制度》的通知.pdf"
     * }
     * ],
     * "knowledge_base_name": "测试0816",
     * "knowledge_base_id": "2278",
     * "override": true,
     * "is_all": false
     * }
     */
    public static FilesParseReq getInnerCallReq(Long kbId, String kbName, KnowledgeBaseFileDTO file, String innerCallUser, String innerCallUserId) {
        FilesParseReq filesParseReq = new FilesParseReq();
        filesParseReq.setIsAll(false);
        filesParseReq.setOverride(true);
        filesParseReq.setKnowledgeBaseId(kbId);
        filesParseReq.setKnowledgeBaseName(kbName);
        filesParseReq.setFiles(List.of(toParseFiles(file)));
        filesParseReq.setNeedAuth(false);
        filesParseReq.setInnerCallUser(innerCallUser);
        filesParseReq.setInnerCallUserId(innerCallUserId);
        return filesParseReq;
    }

    private static File toParseFiles(KnowledgeBaseFileDTO kbFile) {
        File file = new File();
        file.setFileId(kbFile.getId());
        file.setFileName(kbFile.getFileName());
        file.setParseType(kbFile.getParseType());
        file.setFilePath(kbFile.getFilePath());
        file.setConvertedFilePath(kbFile.getConvertedFilePath());
        file.setFileSize(kbFile.getSize());
        file.setParentFileName(kbFile.getParentFileName());
        file.setFolderId(kbFile.getFolderId());
        return file;
    }
}
