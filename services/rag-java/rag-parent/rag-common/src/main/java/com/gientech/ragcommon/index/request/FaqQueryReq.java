package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;


@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(name = "faq修改请求参数")
@Data
public class FaqQueryReq {

    @Schema(name = "kbId",description = "文件kbId")
    private Long kbId;

    @Schema(name = "primitiveName",description = "知识库名称")
    private String primitiveName;

    @Schema(name = "fuzzy",description = "问题或答案(用于模糊搜索)")
    private String fuzzy;

    @Schema(name = "pks",description = "faq主键")
    private List<Long> pks;

    @Schema(name = "relatedPk",description = "相似问关联的字段")
    private List<Long> relatedPks;

    @Schema(name = "status",description = "状态 0:禁用 1 启用  null 所有")
    private Integer status;

    @Schema(name = "folderId",description = "文件夹id")
    private Long folderId;

    @Schema(name = "isNeedFolderId",description = "是否需要folderId参数参与查询")
    private Boolean isNeedFolderId = true;

    @Schema(name = "folderIds",description = "文件夹ids")
    private List<Long> folderIds;

    @Schema(name = "fileId",description = "文件id")
    private Long fileId;

    @Schema(name = "faqFileIds",description = "faq文件ids")
    private List<Long> faqFileIds;

    @Schema(name = "faqType",description = "faq类型  1 原问题  2 相似问")
    private Integer faqType;

    @Schema(name = "pageNo",description = "第几页 默认值 1")
    private Integer pageNo = 1;

    @Schema(name = "pageSize",description = "每页大小 默认值 20")
    private Integer pageSize = 20;

    private Boolean expand = false;
}
