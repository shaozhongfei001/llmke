package com.gientech.ragcommon.index.dto;

import com.gientech.ragcommon.index.enmus.KbFileStatusEnums;
import com.gientech.ragcommon.infrastructure.utils.PdfUtils;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Schema(name = "文件状态")
@Data
public class FileStatusDTO {

    @Schema(name = "id", description = "主键")
    private Long id;

    @Schema(name = "kbId", description = "知识库id")
    private Long kbId;

    @Schema(name = "status", description = "状态 0:删除 1:正常 2:解析中，3:解析成功 4: 解析失败")
    private Integer status;

    @Schema(name = "faqExtractStatus", description = "faq抽取状态 1 未抽取；2 抽取中；3 抽取成功 4 抽取失败 默认值 1")
    private Integer faqExtractStatus;

    @Schema(name = "graphParseStatus", description = "图解析状态 1 未解析；2 解析中 3 解析成功 4 解析失败")
    private Integer graphParseStatus;

    @Schema(name = "uid", description = "文件的uid(uid是前端生成的,文档上传问答使用,通过uid来判断文件解析状态)")
    private String uid;

    @Schema(name = "uid", description = "文件的转换文件路径")
    private String convertedFilePath;

    @Schema(name = "uid", description = "文件的解析文件路径")
    private String parsedFilePath;

    @Schema(name = "pdfPages",description = "pdf页数")
    private Integer pdfPages;

    public Integer getPdfPages() {
        if(KbFileStatusEnums.PARSE_SUCCESS.getValue().equals(status))
            return PdfUtils.getPdfPages(this.convertedFilePath);
        else
            return 0;
    }
}
