package com.gientech.ragcommon.index.request;

import com.gientech.ragcommon.index.enmus.FileListTypeEnums;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import org.springframework.util.CollectionUtils;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Objects;
import java.util.Set;

@Schema(name = "知识库文件查询请求参数", requiredProperties = {"kbId"})
@Data
public class KnowledgeBaseFileQueryReq {

    @Schema(name = "kbId", description = "知识库id")
    private Long kbId;

    @Schema(name = "kbIds", description = "知识库ids")
    private Set<Long> kbIds;

    @Schema(name = "kbNames", description = "知识库命名")
    private List<String> kbNames;

    @Schema(name = "status", description = "状态  1:正常 2:解析中，3:解析成功 4: 解析失败")
    private Integer status;

    @Schema(name = "status", description = "状态  1:正常 2:解析中，3:解析成功 4: 解析失败")
    private List<Integer> statusList;

    @Schema(name = "faqExtractStatus", description = "faq抽取状态 1 未抽取；2 抽取中 3 抽取成功 4 抽取失败")
    private Integer faqExtractStatus;

    @Schema(name = "fuzzy", description = "查询关键字")
    private String fuzzy;

    @Schema(name = "fileListType", description = "列表类型: 1 文件解析列表；2 FAQ解析列表 默认值 1")
    private Integer fileListType = FileListTypeEnums.FILE_LIST.getCode();

    @Schema(name = "kbName", description = "知识库名称")
    private String kbName;

    @Schema(name = "parentFileName", description = "父文件名称")
    private String parentFileName;

    @Schema(name = "folderId", description = "文件夹id")
    private Long folderId;

    @Schema(name = "folderIds", description = "文件夹ids")
    private Set<Long> folderIds;

    @Schema(name = "pageNo", description = "第几页 默认值 1")
    private Long pageNo = 1L;

    @Schema(name = "pageSize", description = "每页大小 默认值 20")
    private Long pageSize = 20L;

    @Schema(name = "scope", description = "own-查询我的,share-查询共享的,all-查询我的加共享的")
    private String scope;

    private boolean withFolder;

    @Schema(name = "showType", description = "展示类型 针对于文件版本管理  1:展示全部 2:展示文件集 3: 散落的文集 默认值 1")
    private Integer showType = 1;

    private String userName;

    private LocalDateTime startTime;

    private LocalDateTime endTime;

    private int[] statusArray;

    public void adjustIdAndIds() {
        if (Objects.nonNull(this.kbId) && CollectionUtils.isEmpty(this.kbIds)) {
            this.kbIds = Set.of(this.kbId);
        }
        if (Objects.nonNull(folderId) && CollectionUtils.isEmpty(this.folderIds)) {
            this.folderIds = Set.of(this.folderId);
        }
    }
}
