package com.gientech.ragauthservice.domain.model;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
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
@TableName("user_info")
@TableComment("用户表")
public class UserInfoDO implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", isNull = false, comment = "主键", isKey = true, isAutoIncrement = true)
    private Long id;

    @Column(name = "user_name", isNull = false, comment = "用户名", length = 128)
    private String userName;

    @Column(name = "gmt_create", comment = "创建时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtCreate;

    @Column(name = "gmt_modified", comment = "更新时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtModified;

    @Column(name = "create_by", comment = "创建人", length = 50)
    private String createBy;

    @Column(name = "update_by", comment = "更新人", length = 50)
    private String updateBy;

    @Column(name = "is_dtl", defaultValue = "0", comment = "逻辑删除 是否删除 1是 0 未删除")
    private String isDtl;

    @Column(name = "user_password", isNull = false, comment = "密码", length = 512)
    private String userPassword;

    @Column(name = "user_realname", comment = "真实姓名", length = 128)
    private String userRealname;

    @Column(name = "user_email", comment = "邮箱", length = 128)
    private String userEmail;

    @Column(name = "url", comment = "用户头像", length = 255)
    private String url;

    @Column(name = "user_phone", comment = "手机", length = 20)
    private String userPhone;

    @Column(name = "status", defaultValue = "1", comment = "状态  1启用 0禁用")
    private Integer status;

    @Column(name = "expire_time", comment = "过期时间", type = MySqlTypeConstant.DATETIME)
    private Date expireTime;

    @Column(name = "miss_num", defaultValue = "0", comment = "密码错误次数")
    private Integer missNum;

    @Column(name = "password_updated", comment = "密码更改时间", type = MySqlTypeConstant.DATETIME)
    private Date passwordUpdated;

    @Column(name = "admin_reset_password", comment = "管理员重置的密码", length = 128)
    private String adminResetPassword;

    @Column(name = "ip", comment = "ip", length = 50)
    private String ip;

    @Column(name = "online_time", comment = "上线时间", type = MySqlTypeConstant.DATETIME)
    private Date onlineTime;

    @Column(name = "organization_id", comment = "机构id")
    private Long organizationId;

    @Column(name = "emp_no", comment = "用户工号", length = 128)
    private String empNo;

    @Column(name = "dept_id", comment = "部门id", length = 30)
    private String deptId;

    @Column(name = "dept_name", comment = "部门名称(冗余字段)", length = 30)
    private String deptName;

    @Column(name = "app_key", comment = "认证key", length = 128)
    private String appKey;

    @Column(name = "resign_date", comment = "离职日期", type = MySqlTypeConstant.DATETIME)
    private Date resignDate;

    @Column(name = "feature", comment = "用户特征", type = MySqlTypeConstant.VARCHAR, length = 1000)
    private String feature;

    @Column(name = "system_source", comment = "用户来源")
    private Integer systemSource;

}
