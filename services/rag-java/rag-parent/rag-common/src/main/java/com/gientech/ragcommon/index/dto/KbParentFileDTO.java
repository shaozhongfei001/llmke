package com.gientech.ragcommon.index.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.google.common.collect.Lists;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.Date;
import java.util.List;

/**
 * <p>
 * 知识库明细
 * </p>
 *
 * @author wudf
 * @since 2024-06-04
 */
@Schema(name = "父文件详情")
@Data
public class KbParentFileDTO {

    @Schema(name = "kbId",description = "知识库id")
    private Long kbId;

    @Schema(name = "parentFileName",description = "父文件名称")
    private String parentFileName;

    @Schema(name = "kbFiles",description = "子文件")
    private List<KnowledgeBaseFileDTO> kbFiles;

}
