package com.gientech.ragcommon.qa.dto;


import com.alibaba.fastjson2.JSONObject;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Getter;
import lombok.Setter;
import org.apache.commons.lang3.StringUtils;

import java.util.Date;

/**
 * @Descrption:
 * @Author:ws
 * @Date:2024/06/04 09:36
 **/
@Schema(name = "问题响应体")
@Setter
@Getter
public class QuestionDTO {

    /**
     * 主键
     */
    @Schema(name = "id",description = "主键")
    private Long id;

    /**
     * 创建时间
     */
    @Schema(name = "gmtCreate",description = "创建时间")
    private Date gmtCreate;

    /**
     * 内容
     */
    @Schema(name = "content",description = "提问内容")
    private String content;

    /**
     * TEXT：文本；VOICE：语音
     */
    @Schema(name = "type",description = "内容类型（TEXT：文本；VOICE：语音）")
    private String type;

    /**
     * 前端生成的uuid
     */
    @Schema(name = "queryId",description = "前端生成的提问id")
    private String queryId;

    @Schema(name = "audioUrl",description ="存储地址")
    private String audioUrl;

    @Schema(name = "filePaths",description ="文档上传问答的文件路径")
    private String filePaths;

    @Schema(name = "filePaths",description ="文档上传问答的文件路径")
    private String currentFiles;

    public void setCurrentFiles(String algParams){
        if(StringUtils.isNotBlank(algParams))
            this.currentFiles = JSONObject.parseObject(algParams).getString("currentFiles");
    }

}
