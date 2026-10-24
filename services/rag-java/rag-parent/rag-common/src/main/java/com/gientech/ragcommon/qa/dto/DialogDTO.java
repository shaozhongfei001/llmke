package com.gientech.ragcommon.qa.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.Date;
import java.util.List;

/**
 * @Descrption: 对话
 * @Author:liutaiyun
 * @Date:2024/05/13 09:35
 **/

@Schema(name = "对话详情")
@Data
public class DialogDTO {

//    @Schema(name = "id",description = "主键")
//    private Long id;

    @Schema(name = "label",description = "对话名称")
    private String label;

    @Schema(name = "sessionId",description = "对话id")
    private String sessionId;

    @Schema(name = "gmtCreate",description = "创建时间")
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss",timezone = "GMT+8")
    private Date gmtCreate;

    @Schema(name = "gmtModified",description = "更新时间")
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss",timezone = "GMT+8")
    private Date gmtModified;

    @Schema(name = "createBy",description = "创建人")
    private String createBy;

    @Schema(name = "createBy",description = "更新人")
    private String updateBy;

    @Schema(name = "filePath",description = "文件地址")
    private String filePath;

    @Schema(name = "configId",description = "配置助手id")
    private Long configId;

    @Schema(name = "kbId",description = "知识库id")
    private Long kbId;

    @Schema(name = "queryReplyPairList",description = "问答对")
    private List<QueryReplyPairDTO> queryReplyPairList;

    /**
     * 助手配置
     */
    private SearchConfigDTO searchConfigDTO;
}
