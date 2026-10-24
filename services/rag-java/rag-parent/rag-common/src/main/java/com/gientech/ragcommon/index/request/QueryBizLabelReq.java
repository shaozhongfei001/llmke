package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.List;

/**
 * @author chenjuan
 * @date 2025/5/8 18:41
 */
@Schema(name = "查询标签请求参数")
@Data
public class QueryBizLabelReq {
    private List<String> kbNames;
}
