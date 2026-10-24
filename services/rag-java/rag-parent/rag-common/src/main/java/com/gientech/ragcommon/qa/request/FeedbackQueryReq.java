package com.gientech.ragcommon.qa.request;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.List;

@Schema(name = "反馈查询条件")
@Data
public class FeedbackQueryReq {

    @Schema(name = "keyList",description = "字段")
    private List<Key> keyList;

    @Schema(name = "fuzzy",description = "查询关键字")
    private String fuzzy;

    @Schema(name = "startTime",description = "开始时间")
    private String startTime;

    @Schema(name = "endTime",description = "结束时间")
    private String endTime;

    @Schema(name = "pageSize",description = "每页大小,默认值20")
    private Long pageSize = 20L;

    @Schema(name = "pageNo",description = "第几页 默认值1")
    private Long pageNo = 1L;

    @Data
    public static class Key{
        private String column;
        private String columnValue;
    }
}
