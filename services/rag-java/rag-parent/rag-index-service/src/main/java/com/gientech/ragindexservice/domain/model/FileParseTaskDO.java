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
import java.math.BigDecimal;

@Builder
@Data
@NoArgsConstructor
@AllArgsConstructor
@TableName("file_parse_task")
public class FileParseTaskDO implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", comment = "主键", isNull = false, isKey = true ,isAutoIncrement = true)
    private Long id;

    @Column(name = "kb_id", comment = "知识库id", isNull = false)
    private Long kbId;

    @Column(name = "kb_name", comment = "知识库名称", length = 256)
    private String kbName;

    @Column(name = "file_id", comment = "文件id", isNull = false)
    private Long fileId;

    @Column(name = "file_name", comment = "文件库名称", length = 256)
    private String fileName;

    @Column(name = "task_info", comment = "任务详情", type = MySqlTypeConstant.TEXT)
    private String taskInfo;

    @Column(name = "status", comment = "状态 -1:删除 1:待处理 2:处理中,3:重试中 4: 成功 5: 处理失败", defaultValue = "1")
    private Integer status;

    @Column(name = "start_time", comment = "解析开始时间",type = MySqlTypeConstant.TIMESTAMP)
    private Date startTime;

    @Column(name = "end_time", comment = "解析结束时间",type = MySqlTypeConstant.TIMESTAMP)
    private Date endTime;

    @Column(name = "retry_limit", comment = "重试限制次数")
    private Integer retryLimit;

    @Column(name = "retry_times", comment = "已经重试次数", defaultValue = "0")
    private Integer retryTimes;

    @Column(name = "error_msg", comment = "失败原因", type = MySqlTypeConstant.TEXT)
    private String errorMsg;

    @Column(name = "create_by", comment = "创建人", length = 30)
    private String createBy;

    @Column(name = "gmt_create", comment = "创建时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtCreate;

    @Column(name = "modify_by", comment = "修改人", length = 30)
    private String modifyBy;

    @Column(name = "gmt_modified", comment = "修改时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtModified;

}
