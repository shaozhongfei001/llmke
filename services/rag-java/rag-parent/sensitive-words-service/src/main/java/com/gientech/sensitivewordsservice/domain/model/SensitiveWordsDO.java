package com.gientech.sensitivewordsservice.domain.model;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.gientech.ragcommon.infrastructure.typehandler.LinkedHashSetTypeHandler;
import com.gitee.sunchenbin.mybatis.actable.annotation.Column;
import com.gitee.sunchenbin.mybatis.actable.constants.MySqlTypeConstant;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.Date;
import java.util.LinkedHashSet;

@Builder
@Data
@NoArgsConstructor
@AllArgsConstructor
@TableName("sensitive_words")
public class SensitiveWordsDO implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", isNull = false, comment = "主键", isKey = true, isAutoIncrement = true)
    private Long id;

    @Column(name = "gmt_create", comment = "创建时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtCreate;

    @Column(name = "gmt_modified", comment = "修改时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtModified;

    @Column(name = "name", comment = "敏感词库名称", length = 512)
    private String name;

    @Column(name = "descript", comment = "描述", length = 512)
    private String descript;

    @Column(name = "words", comment = "敏感词详情", type = MySqlTypeConstant.LONGTEXT)
    @TableField(value = "words", typeHandler = LinkedHashSetTypeHandler.class)
    private LinkedHashSet<String> words;

    @Column(name = "status", comment = "状态，1正常，-1删除")
    private Integer status;

//    public LinkedHashSet<String> getSplitedWords(){
//        return Optional.ofNullable(words).map(str -> {
//                    String substring = str.substring(1, str.length() - 1);
//                    String[] split = substring.split(",");
//                    return Arrays.stream(split).collect(Collectors.toCollection(LinkedHashSet<String>::new));
//            }).orElseGet(LinkedHashSet::new);
//    }

}
