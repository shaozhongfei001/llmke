package com.gientech.ragindexservice.domain.model;

import com.baomidou.mybatisplus.annotation.*;
import com.gitee.sunchenbin.mybatis.actable.annotation.Column;
import com.gitee.sunchenbin.mybatis.actable.annotation.TableComment;
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
@TableName("knowledge_base")
@TableComment("知识库")
public class KnowledgeBaseDO implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", isNull = false, isKey = true, isAutoIncrement = true)
    private Long id;

    @Column(name = "kb_name", comment = "知识库名称", length = 128)
    private String kbName;

    @Column(name = "primitive_name", comment = "知识库原始名称,对应算法知识库的名称", length = 128)
    private String primitiveName;

    @Column(name = "kb_type", defaultValue = "1", comment = "知识库类型 1:知识库 2: 文档上传问答")
    private Integer kbType;

    @Column(name = "kb_des", comment = "描述", length = 255)
    private String kbDes;

    @Column(name = "source_url", comment = "路径", length = 128)
    private String sourceUrl;

    @Column(name = "status", defaultValue = "1", comment = "状态 0:删除;1正常，默认值1")
    private Integer status;

    @Column(name = "config", comment = "知识库解析配置", type = MySqlTypeConstant.TEXT)
    private String config;

    @TableField(updateStrategy = FieldStrategy.IGNORED)
    @Column(name = "kb_label", comment = "知识库标签", length = 128)
    private String kbLabel;

    @Column(name = "create_by", comment = "创建人", length = 30)
    private String createBy;

    @Column(name = "gmt_create", comment = "创建时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtCreate;

    @Column(name = "modify_by", comment = "修改人", length = 30)
    private String modifyBy;

    @Column(name = "gmt_modified", comment = "修改时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtModified;

    @Column(name = "platform", comment = "上层应用平台", length = 128)
    private String platform;

    @Column(name = "private_kb", defaultValue = "0", comment = "是否私有知识库 0：非私有 1：私有")
    private Integer privateKb;

}
