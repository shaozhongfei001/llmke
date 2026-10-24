package com.gientech.ragcommon.auth.dto;

import lombok.Data;

/**
 * @Descrption:
 * @Author:liutaiyun
 * @Date:2024/08/27 14:38
 **/
@Data
public class SystemVersionDTO {

    /**
     * 主版本号
     */
    private String version;

    /**
     * 子版本
     */
    private String subVersion;

    /**
     * 版本详情（变更内容）
     */
    private String detail;

    /**
     * 版本创建日期
     */
    private String Date;
}
