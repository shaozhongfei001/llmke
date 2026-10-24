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

/**
 * @Desc 模型信息表
 * @Author ZhenPanHong
 * @Date 2025/3/5 13:38
 */
@Builder
@Data
@NoArgsConstructor
@AllArgsConstructor
@TableName(value = "model_info")
@TableComment("模型信息表")
public class ModelInfoDO implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", comment = "主键", isNull = false, isKey = true, isAutoIncrement = true)
    private Long id;

    @Column(name = "model_name", comment = "模型名称", length = 128)
    private String modelName;

//    @TableField(value = "`type`")
//    @Column(name = "type", comment = "模型类型,1-Baichuan、2-Qwen、3-GLM、4-Xinference", type = MySqlTypeConstant.TINYINT)
//    private Integer type;

    @TableField(value = "`type`")
    @Column(name = "type", comment = "模型使用类型: 1:LLM大语言模型、2:Embedding嵌入、3:rerank排序、4:MultiModel图片解析", type = MySqlTypeConstant.TINYINT,defaultValue = "1")
    private Integer type;

    @Column(name = "model_protocol", comment = "模型传输协议,1-Baichuan、2-Qwen、3-GLM、4-openAI", type = MySqlTypeConstant.TINYINT)
    private Integer modelProtocol;

    @Column(name = "model_ide", comment = "待接入的模型ID", length = 128)
    private String modelIde;

    @Column(name = "api_key", comment = "APIkey", length = 255)
    private String apiKey;

    @Column(name = "url", comment = "请求URL", length = 255)
    private String url;

    @TableField(value = "`dec`")
    @Column(name = "dec", comment = "说明", length = 255)
    private String dec;

    @TableField(value = "`status`")
    @Column(name = "status", comment = "状态,0-不可用,1-可用,3-检测中", type = MySqlTypeConstant.TINYINT)
    private Integer status;

    @Column(name = "error_msg", comment = "报错信息", length = 500)
    @TableField(updateStrategy = FieldStrategy.IGNORED)
    private String errorMsg;

    @TableField(fill = FieldFill.INSERT)
    @TableLogic(value = "0", delval = "1")
    @Column(name = "is_dtl", comment = "逻辑删除,0-未删除,1-已删除,默认为0", length = 1)
    private String isDtl;

//    @Column(name = "trace", defaultValue = "0", comment = "溯源策略(deepseek相关模型的功能) 0:没有溯源策略 1:有溯源策略")
//    private Integer trace;

    @Column(name = "thinking", defaultValue = "0", comment = "推理思考(qwen3相关模型的功能) 0:没有推理思考功能 1:有推理思考功能")
    private Integer thinking;

    @TableField(fill = FieldFill.INSERT)
    @Column(name = "gmt_create", comment = "创建时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtCreate;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    @Column(name = "gmt_modified", comment = "更新时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtModified;

    @TableField(fill = FieldFill.INSERT)
    @Column(name = "create_by", comment = "创建人", length = 50)
    private String createBy;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    @Column(name = "update_by", comment = "更新人", length = 50)
    private String updateBy;
}