package com.gientech.ragqaservice.domain.entity;


import com.gientech.ragcommon.qa.entity.Config;
import lombok.Getter;
import lombok.Setter;

import java.io.Serializable;
import java.util.Date;


@Getter
@Setter
public class Dialogue implements Serializable {

    private Long id;


    /**
     * Dialogue名称
     */
    private String label;

    /**
     * 对话id
     */
    private String sessionId;

    /**
     * 状态 0:删除;1正常，默认值1
     */
    private Integer status;

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

    /**
     * 助手配置
     */
    private Config config;

    /**
     * 系统类型：0.智能会话，1.知识索引 2.临时会话
     */
    private Integer sysType;

    /**
     * 检索配置id
     */
    private Long configId;

    /**
     * 检索配置历史信息
     */
    private String configHistory;

    /**
     * 知识库id
     */
    private Long kbId;
}
