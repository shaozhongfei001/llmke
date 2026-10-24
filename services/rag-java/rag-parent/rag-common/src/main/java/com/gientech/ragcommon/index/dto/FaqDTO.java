package com.gientech.ragcommon.index.dto;

import com.alibaba.fastjson2.JSONObject;
import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import com.gientech.ragcommon.index.utils.BizLabelUtils;
import com.gientech.ragcommon.infrastructure.utils.PdfUtils;
import com.google.common.collect.Lists;
import io.micrometer.common.util.StringUtils;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import org.springframework.util.CollectionUtils;

import java.util.Arrays;
import java.util.List;
import java.util.Objects;

@Schema(name = "faq信息")
@Data
public class FaqDTO {

    @JsonSerialize(using = ToStringSerializer.class)
    @Schema(name = "pk", description = "问答对id")
    private Long pk;

    @Schema(name = "pk", description = "相似问关联的pk")
    @JsonSerialize(using = ToStringSerializer.class)
    private Long relatedPk;

    @Schema(name = "question", description = "问题")
    private String question;

    @Schema(name = "answer", description = "答案")
    private String answer;

    @Schema(name = "status", description = "启用状态，0:待启用，1：已启用")
    private Integer status;

    @Schema(name = "sourceFile", description = "文件路径")
    private String sourceFile;

    @Schema(name = "pdfPages", description = "pdf文件的页数")
    private Integer pdfPages;

    @Schema(name = "fileName", description = "文件名")
    private String fileName;

    @Schema(name = "fileId", description = "文档id")
    private Long fileId;

    //    @JsonFormat(pattern = "yyyy-MM-dd",timezone = "GMT+8")
    @Schema(name = "reviseDate", description = "修订实时间")
    private String reviseDate;

    @Schema(name = "similarQuestions", description = "相似问列表")
    private List<FaqDTO> similarQuestions = Lists.newArrayList();

    @JsonIgnore
    @Schema(name = "pageContent", description = "问题@@答案")
    private String pageContent;

    @JsonIgnore
    @Schema(name = "metadata", description = "metadata数据")
    private JSONObject metadata;

    @Schema(name = "faqType", description = " 1原faq ,2相似问")
    private Integer faqType;

    @Schema(name = "folderId", description = "文件夹id")
    private Long folderId;

    @Schema(name = "folderName", description = "文件夹名称")
    private String folderName;

    @Schema(name = "type", description = "数据类型 1 文件夹 2 文件  3 faq 默认值3")
    private Integer dataType = 3;

    @Schema(name = "documentId", description = "原文档id")
    private Long documentId;

    @Schema(name = "faqFileId", description = "faq管理的文件id")
    private Long faqFileId;

    private String label;

    private List<String> labels;

    private Integer permission;


    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof FaqDTO)) return false;
        FaqDTO faqDTO = (FaqDTO) o;
        return pk.equals(faqDTO.pk);
    }

    @Override
    public int hashCode() {
        return Objects.hash(pk);
    }


    /**
     * file_id是复制文件到FAQ管理的文件id
     * docId是FAQ抽取的文件id
     *
     * @return
     */
    @JsonIgnore
    public Long getCommonId() {
        if (dataType.equals(1)) {
            return folderId;
        }
        if (dataType.equals(3)) {
            return faqFileId;
        }
        return fileId;
    }

    @JsonIgnore
    public String getCommonIdStr() {
        if (dataType.equals(1)) {
            return "folder_" + folderId;
        }
        if (dataType.equals(3)) {
            return "file_" + faqFileId;
        }
        return "file_" + fileId;
    }

    public String getLabel() {
        return CollectionUtils.isEmpty(labels) ? "" : String.join(",", labels);
    }

    public void setLabelsByLabel(String label) {
        if (!CollectionUtils.isEmpty(labels) && StringUtils.isBlank(label)) {
            this.label = String.join(",", labels);
            return;
        }
        this.label = label;
        this.labels = Arrays.asList(BizLabelUtils.safeGetLabels(label, ","));
    }

    public Integer getPdfPages() {
        return PdfUtils.getPdfPages(this.sourceFile);
    }
}
