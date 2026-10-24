package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(name = "faq润色请求参数")
@Data
public class FaqPolishReq {

    @NotNull(message = "kbId不能为空")
    @Schema(name = "kbId" , description = "知识库id")
    private Long kbId;

//    @NotNull(message = "fileId不能为空")
    @Schema(name = "fileId" , description = "文件id")
    private Long fileId;

    @NotEmpty(message = "pks不能为空")
    @Schema(name = "pks" , description = "faq主键")
    private List<Long> pks;
}
