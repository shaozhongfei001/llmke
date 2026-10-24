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
@TableName("question")
@TableComment("答案表")
public class QuestionDO implements Serializable {

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

    @Column(name = "content", comment = "答案内容", type = MySqlTypeConstant.TEXT)
    private String content;

    @Column(name = "type", defaultValue = "1", comment = "TEXT：文本；VOICE：语音", length = 32)
    private String type;

    @Column(name = "front_uuid", comment = "前端生成的uuid", length = 128)
    private String frontUuid;

    @Column(name = "alg_model", comment = "模型算法", length = 128)
    private String algModel;

    @Column(name = "alg_params", comment = "模型参数(json)", type = MySqlTypeConstant.TEXT)
    private String algParams;

    @Column(name = "knowledge_base_name", comment = "知识库名称", length = 128)
    private String knowledgeBaseName;

    @Column(name = "knowledge_params", comment = "知识库参数(json)", type = MySqlTypeConstant.TEXT)
    private String knowledgeParams;

    @Column(name = "audio_url", comment = "音频地址", length = 512)
    private String audioUrl;

}
