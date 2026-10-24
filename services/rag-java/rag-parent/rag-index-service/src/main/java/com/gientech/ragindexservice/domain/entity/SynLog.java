package com.gientech.ragindexservice.domain.entity;
import lombok.Builder;
import lombok.Data;
import java.io.Serializable;
import java.util.Date;

/**
 * <p>
 * 日志
 * </p>
 *
 * @author wudf
 * @since 2024-08-27
 */
@Builder
@Data
public class SynLog implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 主键
     */
    private Long id;

    /**
     * 知识库id
     */
    private Long kbId;

    /**
     * 目标id（知识库id）
     */
    private Long targetId;

    /**
     * 日志类型 1:文件解析;2FAQ抽取
     */
    private Integer logType;

    /**
     * 异常码 (如果为-1的话，接口不可用)
     */
    private String errorCode;

    /**
     * 异常信息
     */
    private String errorMessage;

    /**
     * 异常信息详情
     */
    private String errorDetail;

    /**
     * 创建时间
     */
    private Date gmtCreate;

    /**
     * 更新时间
     */
    private Date gmtModified;

    /**
     * 创建人
     */
    private String createBy;

    /**
     * 更新人
     */
    private String updateBy;
}
