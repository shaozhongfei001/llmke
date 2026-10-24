package com.gientech.ragqaservice.domain.model;

import com.alibaba.fastjson2.JSONObject;
import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.gitee.sunchenbin.mybatis.actable.annotation.*;
import com.gitee.sunchenbin.mybatis.actable.constants.MySqlTypeConstant;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.io.Serializable;
import java.util.Date;

@Builder
@Data
@NoArgsConstructor
@AllArgsConstructor
@TableName("search_config")
@TableComment("问题查询配置表")
public class SearchConfigDO implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", isNull = false, comment = "主键" ,isKey = true ,isAutoIncrement = true)
    private Long id;

    @Column(name = "status", defaultValue = "1", comment = "状态 0:禁用；1:正常 默认值1")
    private Integer status;

    @Column(name = "is_default", defaultValue = "1", comment = "是否默认 0:否；1:是 默认值1")
    private Integer isDefault;

    @Column(name = "config_json", comment = "配置详情", type = MySqlTypeConstant.TEXT)
    private String configJson;

    @Column(name = "name", comment = "名称", length = 50)
    private String name;

    @Column(name = "des", comment = "描述", length = 255)
    private String des;

    @Column(name = "create_by", comment = "创建人", length = 30)
    private String createBy;

    @Column(name = "gmt_create", comment = "创建时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtCreate;

    @Column(name = "modify_by", comment = "修改人", length = 30)
    private String modifyBy;

    @Column(name = "gmt_modified", comment = "修改时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtModified;

    @Column(name = "sensitive_word_ids", comment = "敏感词id", length = 255)
    private String sensitiveWordIds;

    @Column(name = "default_answer", comment = "默认回答(sensitive_word_ids不为空时,必填)", length = 255)
    private String defaultAnswer;

    @Column(name = "enabled_faq", comment = "是否开启faq(0:否;1:是)", defaultValue = "0")
    private Integer enabledFaq;

    /**
     * 是否强依赖知识库(0:否;1:是)
     */
    @Column(name = "depend_on_kb", comment = "是否强依赖知识库(0:否;1:是)", defaultValue = "0")
    private Integer dependOnKb;

    @Column(name = "is_del", comment = "是否删除 -1 删除  1 正常 默认值1", defaultValue = "1")
    private Integer isDel;

    public JSONObject getConfigObj(){
        return JSONObject.parseObject(this.getConfigJson());
    }


}
