package com.gientech.ragqaservice.domain.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import lombok.Data;

import java.io.Serializable;
import java.util.Date;

@Data
public class Feedback implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long id;

    /**
     * 答案id
     */
    private Long answerId;

    /**
     *
     */
    private String searchConfigName;

    /**
     * 0：踩；1：赞
     */
    private Integer restult;

    /**
     * 用户真实名称
     */
    private String userRealname;

    /**
     * 用户登录名
     */
    private String userName;

    /**
     * 部门名称
     */
    private String deptName;

    /**
     * 手机
     */
    private String userPhone;

    /**
     * 理解问题有误
     */
    private String queError;

    /**
     * 回答不佳
     */
    private String ansPoor;

    /**
     * 格式错误
     */
    private String formatError;

    /**
     * 有害信息
     */
    private String harmfulInfo;

    /**
     * 其他
     */
    private String othres;

    /**
     * 补充说明
     */
    private String supplementExplain;

    /**
     * 理想回答
     */
    private String idealAnswer;

    /**
     * 创建时间
     *
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
}
