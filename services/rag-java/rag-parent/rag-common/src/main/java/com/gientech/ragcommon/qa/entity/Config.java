package com.gientech.ragcommon.qa.entity;

import com.alibaba.fastjson2.JSONObject;
import com.gientech.ragcommon.index.constant.KbConfigConstant;
import com.gientech.ragcommon.qa.constant.AIConstant;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;

import java.io.Serializable;
import java.util.Date;
import java.util.Map;

/**
 * <p>
 * 问题查询配置表
 * </p>
 *
 * @author wudf
 * @since 2024-06-18
 */
@Data
@Slf4j
public class Config implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 主键
     */
    private Long id;

    /**
     * 状态 0:禁用；1:正常 默认值1
     */
    private Integer status;

    /**
     * 是否默认 0:否；1:是 默认值1
     */
    private Integer isDefault;

    /**
     * 配置详情
     */
    private String configJson;

    /**
     * 名称
     */
    private String name;

    /**
     * 描述
     */
    private String des;

    /**
     * 创建人
     */
    private String createBy;

    /**
     * 创建时间
     */
    private Date gmtCreate;

    /**
     * 修改人
     */
    private String modifyBy;

    /**
     * 修改时间
     */
    private Date gmtModified;

    /**
     * 敏感词
     */
    private String sensitiveWordIds;

    /**
     * 默认回答(sensitive_word_ids不为空时,必填)
     */
    private String defaultAnswer;

    /**
     * 是否开启faq(0:否;1:是)
     */
    private Integer enabledFaq;

    /**
     * 是否强依赖于知识库（0:否;1:是）
     */
    private Integer dependOnKb;

    /**
     * 是否删除 -1 删除  1 正常 默认值1
     */
    private Integer isDel;


    public void setModelIntoKbConfMap(Map<String, Object> map) {
        JSONObject configObj = JSONObject.parseObject(configJson);
        map.put(KbConfigConstant.MODEL_NAME, configObj.get(AIConstant.MODEL_NAME));
        map.put(KbConfigConstant.MULTI_MODEL_NAME, configObj.get(AIConstant.MULTI_MODEL_NAME));
    }
}
