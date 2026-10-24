package com.gientech.ragauthservice.domain.model;

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
@TableName("user_operate")
public class UserOperateDO implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", comment = "主键", isNull = false, isKey = true ,isAutoIncrement = true)
    private Long id;

    @Column(name = "gmt_created", comment = "创建时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtCreated;

    @Column(name = "gmt_modified", comment = "创建时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtModified;

    @Column(name = "name", comment = "方法名称", length = 255)
    private String name;

    @Column(name = "url", comment = "方法url", length = 255)
    private String url;

    @Column(name = "start_time", comment = "接口请求开始时间", type = MySqlTypeConstant.DATETIME)
    private Date startTime;

    @Column(name = "end_time", comment = "接口请求结束时间", type = MySqlTypeConstant.DATETIME)
    private Date endTime;

    @Column(name = "user_id", comment = "用户id")
    private Long userId;

    @Column(name = "user_name", comment = "用户名称", length = 128)
    private String userName;

    @Column(name = "params", comment = "参数", type = MySqlTypeConstant.TEXT)
    private String params;

    @Column(name = "ip", comment = "ip", length = 20)
    private String ip;

    @Column(name = "success", comment = "接口是否请求成功 0 否  1是 默认值1")
    private Integer success;

}
