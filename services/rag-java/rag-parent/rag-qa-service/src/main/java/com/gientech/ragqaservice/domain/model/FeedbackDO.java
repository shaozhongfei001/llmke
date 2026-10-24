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
@TableName("feedback")
@TableComment("反馈表")
public class FeedbackDO implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", isNull = false ,isKey = true ,isAutoIncrement = true)
    private Long id;

    @Column(name = "answer_id", comment = "答案id")
    private Long answerId;

    @Column(name = "restult", comment = "0：踩；1：赞")
    private Integer restult;

    @Column(name = "user_name", comment = "用户登录名", length = 64)
    private String userName;

    @Column(name = "user_realname", comment = "用户真实名称", length = 64)
    private String userRealname;

    @Column(name = "dept_name", comment = "部门名称", length = 30)
    private String deptName;

    @Column(name = "user_phone", comment = "手机", length = 20)
    private String userPhone;

    @Column(name = "que_error", comment = "理解问题有误", length = 255)
    private String queError;

    @Column(name = "ans_poor", comment = "回答不佳", length = 255)
    private String ansPoor;

    @Column(name = "format_error", comment = "格式问题", length = 255)
    private String formatError;

    @Column(name = "harmful_info", comment = "有害信息", length = 255)
    private String harmfulInfo;

    @Column(name = "othres", comment = "其他", length = 255)
    private String othres;

    @Column(name = "supplement_explain", comment = "补充说明", type = MySqlTypeConstant.TEXT)
    private String supplementExplain;

    @Column(name = "ideal_answer", comment = "理想回答", type = MySqlTypeConstant.TEXT)
    private String idealAnswer;

    @Column(name = "gmt_create", comment = "创建时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtCreate;

    @Column(name = "gmt_modified", comment = "更新时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtModified;

    @Column(name = "create_by", comment = "创建人", length = 50)
    private String createBy;

    @Column(name = "update_by", comment = "更新人", length = 50)
    private String updateBy;

    @Column(name = "is_del", comment = "是否删除 -1 删除  1 正常 默认值1", defaultValue = "1")
    private Integer isDel;

}
