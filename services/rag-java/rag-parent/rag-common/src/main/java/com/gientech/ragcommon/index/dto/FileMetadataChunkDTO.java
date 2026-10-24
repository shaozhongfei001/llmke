package com.gientech.ragcommon.index.dto;

/**
 * @author: shirleychen
 * @date 2025/11/21 13:42
 * @description
 */

import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class FileMetadataChunkDTO {
    private String source;
    @JsonProperty("file_path")
    private String filePath;
    @JsonProperty("document_id")
    private String documentId;
    @JsonProperty("file_id")
    private Long fileId;
    @JsonProperty("knowledge_base_name")
    private String knowledgeBaseName;
    @JsonProperty("file_size")
    private String fileSize;
    private String title;
    private String type;
    private Object position;
    @JsonProperty("page_number")
    private List<Integer> pageNumber;
    @JsonProperty("page_size")
    private Object pageSize;
    private Object offset;
    @JsonProperty("revise_date")
    private String reviseDate;
    @JsonProperty("parent_file_name")
    private String parentFileName;
    private Long pk;
    @JsonProperty("pic_url_list")
    private List<String> picUrlList;
    @JsonProperty("pic_offset_list")
    private List<Integer> picOffsetList;
    @JsonProperty("pic_children_id_list")
    private List<Long> picChildrenIdList;
    @JsonProperty("need_filtered")
    private Boolean needFiltered;
    @JsonProperty("title_path")
    private String titlePath;
    @JsonProperty("chunk_index")
    private Integer chunkIndex;
    private List<String> labels;
    @JsonProperty("folder_id")
    private Long folderId;
    private Integer status;
    @JsonProperty("create_time")
    private String createTime;
    @JsonProperty("update_time")
    private String updateTime;
    @JsonIgnore
    private Integer total;
}
