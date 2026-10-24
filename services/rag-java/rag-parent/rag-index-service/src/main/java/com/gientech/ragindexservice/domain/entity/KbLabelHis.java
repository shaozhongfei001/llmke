package com.gientech.ragindexservice.domain.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.math.BigDecimal;
import java.util.Date;
import java.util.LinkedHashSet;

@AllArgsConstructor
@NoArgsConstructor
@Data
public class KbLabelHis {

    private static final long serialVersionUID = 1L;

    private Long id;

    /**
     * 知识库id
    */
    private Long kbId;

    /**
     * 知识库使用的标签
    */
    private String labe;

    /**
     * 是否删除 -1 删除  1 正常 默认值1
    */
    private Integer isDel;

    /**
     * 创建人
    */
    private String createBy;

    /**
     * 创建时间
    */
    private Date gmtCreate;

    /**
     * 修改人
    */
    private String modifyBy;

    /**
     * 修改时间
    */
    private Date gmtModified;

}
