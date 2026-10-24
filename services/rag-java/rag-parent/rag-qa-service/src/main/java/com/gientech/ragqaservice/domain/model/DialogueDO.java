package com.gientech.ragqaservice.domain.model;

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
@TableName("dialogue")
@TableComment("对话表")
public class DialogueDO implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", isNull = false ,isKey = true ,isAutoIncrement = true)
    private Long id;

    @Column(name = "label", comment = "对话名称", length = 255)
    private String label;

    @Column(name = "session_id", comment = "对话id", length = 128)
    private String sessionId;

    @Column(name = "status", defaultValue = "1", comment = "状态 0:删除;1正常，默认值1")
    private Integer status;

    @Column(name = "gmt_create", comment = "创建时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtCreate;

    @Column(name = "gmt_modified", comment = "更新时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtModified;

    @Column(name = "create_by", comment = "创建人", length = 50)
    private String createBy;

    @Column(name = "update_by", comment = "更新人", length = 50)
    private String updateBy;

    @Column(name = "sys_type", comment = "系统类型：0.智能会话，1.知识索引,3 临时会话")
    private Integer sysType;

    @Column(name = "config", comment = "配置信息", type = MySqlTypeConstant.TEXT)
    private String config;

    @Column(name = "config_id", comment = "检索配置id")
    private Long configId;

    @Column(name = "config_history", comment = "检索配置历史信息", type = MySqlTypeConstant.TEXT)
    private String configHistory;

    @Column(name = "kb_id", comment = "知识库id", length = 128)
    private Long kbId;

}
