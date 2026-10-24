package com.gientech.ragcommon.qa.dto;


import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * @Descrption:
 * @Author:ws
 * @Date:2024/06/04 09:36
 **/
@Schema(name = "")
@Data
public class MinioAudioVTO {

    @Schema(name = "audioUrl",description ="存储地址")
    private String audioUrl;


    @Schema(name = "content",description = "语音识别内容")
    private String content;

}
