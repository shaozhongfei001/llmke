package com.gientech.tools.database.interfaces.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.Map;

@Schema(name = "结果对象")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ResultDto<T> implements Serializable {
    // 处理是否成功
    private boolean success;

    // 业务状态码（内部自定义）
    private String code;

    // 详细消息（可包含技术或业务说明）
    private String message;

    // 响应数据
    private T data;

    // 附加信息（可存放额外的上下文数据）
    private Map<String, Object> extra;
}
