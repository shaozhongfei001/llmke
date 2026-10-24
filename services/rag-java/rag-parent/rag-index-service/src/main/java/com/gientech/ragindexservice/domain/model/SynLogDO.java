package com.gientech.ragindexservice.domain.model;

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
@TableName("syn_log")
@TableComment("日志")
public class SynLogDO implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", isNull = false, comment = "主键" ,isKey = true ,isAutoIncrement = true)
    private Long id;

    @Column(name = "kb_id", comment = "知识库id")
    private Long kbId;

    @Column(name = "target_id", comment = "目标id（知识库id）")
    private Long targetId;

    @Column(name = "log_type", comment = "日志类型 1:文件解析;2FAQ抽取")
    private Integer logType;

    @Column(name = "error_code", comment = "异常码 (如果为-1的话，接口不可用)", length = 16)
    private String errorCode;

    @Column(name = "error_message", comment = "异常信息", type = MySqlTypeConstant.TEXT)
    private String errorMessage;

    @Column(name = "error_detail", comment = "异常信息详情", type = MySqlTypeConstant.TEXT)
    private String errorDetail;

    @Column(name = "gmt_create", comment = "创建时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtCreate;

    @Column(name = "gmt_modified", comment = "更新时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtModified;

    @Column(name = "create_by", comment = "创建人", length = 50)
    private String createBy;

    @Column(name = "update_by", comment = "更新人", length = 50)
    private String updateBy;

}
