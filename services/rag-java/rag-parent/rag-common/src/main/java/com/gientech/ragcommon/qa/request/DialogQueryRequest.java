package com.gientech.ragcommon.qa.request;

import com.gientech.ragcommon.qa.enmus.SysTypeEnums;
import com.google.common.collect.Lists;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

/**
 * @Descrption: 对话查询请求入参对象
 * @Author:liutaiyun
 * @Date:2024/05/13 15:20
 **/
@Schema(name = "对话分页查询条件",requiredProperties = {"label"})
@Data
public class DialogQueryRequest {

    @Schema(name = "sysType",description = "系统类型(INT_SESSION:智能会话;KNO_INDEX:知识索引)")
    private SysTypeEnums sysType =SysTypeEnums.KNO_INDEX;

    /**
     * 对话名称（模糊查询）
     */
    @Schema(name = "label",description = "对话名称")
    private String label;

    /**
     * 请求页码
     */
    @Schema(name = "pageNo",description = "第几页 默认值 1")
    private Long pageNo=1L;

    /**
     * 页面大小
     */
    @Schema(name = "pageSize",description = "每页大小 默认值 20")
    private Long pageSize=20L;
}
