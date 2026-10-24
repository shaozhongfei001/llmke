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
@TableName("answer")
@TableComment("答案表")
public class AnswerDO implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", isNull = false ,isKey = true ,isAutoIncrement = true)
    private Long id;

    @Column(name = "gmt_create", comment = "创建时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtCreate;

    @Column(name = "gmt_modified", comment = "修改时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtModified;

    @Column(name = "dialogue_id", comment = "对话id")
    private Long dialogueId;

    @Column(name = "question_id", comment = "问题id")
    private Long questionId;

    @Column(name = "content", comment = "答案内容", type = MySqlTypeConstant.TEXT)
    private String content;

    @Column(name = "type", defaultValue = "1", comment = "TEXT：文本；VOICE：语音", length = 32)
    private String type;

    @Column(name = "reference", comment = "参考内容(json)", type = MySqlTypeConstant.MEDIUMBLOB)
    private String reference;

    @Column(name = "database_reference", comment = "数据库召回", type = MySqlTypeConstant.TEXT)
    private String databaseReference;


    @Column(name = "log_result", comment = "算法评测日志(json)", type = MySqlTypeConstant.TEXT)
    private String logResult;

    @Column(name = "retrieve_recall_Param", comment = "知识检索召回测试的参数", type = MySqlTypeConstant.TEXT)
    private String retrieveRecallParam;

    @Column(name = "recommend_question", comment = "问题推荐", type = MySqlTypeConstant.TEXT)
    private String recommendQuestion;

    @Deprecated
    @Column(name = "llm_type", defaultValue = "1", comment = "推理类型 1:推理接口, 2:表格推理接口 默认值1", length = 10)
    private Integer llmType;

    @Column(name = "result_type", comment = "响应的类型 1:正常大模型推理; 2:FAQ; 3 命中敏感词;4 强知识依赖;5文档上传问答;6 表格问答", length = 10)
    private Integer resultType;

    @Column(name = "resp_time", comment = "问答接口响应时间(毫秒)")
    private Long respTime;

}
