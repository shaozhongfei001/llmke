package com.gientech.ragcommon.qa.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.Date;
import java.util.Objects;


@Schema(name = "查询配置详情")
@Data
public class SearchConfigDTO {

    @Schema(name = "id", description = "主键")
    private Long id;

    @Schema(name = "status", description = "状态 0:禁用；1:正常 默认值1")
    private Integer status;

    @Schema(name = "isDefault", description = "是否默认 0:否；1:是 默认值1")
    private Integer isDefault;

    @Schema(name = "configJson", description = "配置详情")
    private String configJson;

    @Schema(name = "name", description = "名称")
    private String name;

    @Schema(name = "des", description = "描述")
    private String des;

    @Schema(name = "createBy", description = "创建人")
    private String createBy;

    @Schema(name = "gmtCreate", description = "创建时间")
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss",timezone = "GMT+8")
    private Date gmtCreate;

    @Schema(name = "permission",description = "数据权限 0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限")
    private Integer permission;

    @Schema(name = "sensitiveWordIds", description = "敏感词")
    private String sensitiveWordIds;

    @Schema(name = "defaultAnswer", description = "默认回答(sensitive_word_ids不为空时,必填)")
    private String defaultAnswer;

    /**
     * 是否是默认配置
     */
    private Boolean model = Boolean.FALSE;

    /**
     * 是否开启faq(0:否;1:是)
     */
    private Integer enabledFaq;

    @Schema(name = "dependOnKb", description = "是否强依赖知识库 0:否；1:是 默认值1")
    private Integer dependOnKb;

    @Schema(name = "isDel", description = "是否删除 -1 删除  1 正常 默认值1")
    private Integer isDel;

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        SearchConfigDTO that = (SearchConfigDTO) o;
        return id.equals(that.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }
}
