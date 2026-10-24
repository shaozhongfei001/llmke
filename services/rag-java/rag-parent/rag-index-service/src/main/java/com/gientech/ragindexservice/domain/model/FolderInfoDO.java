package com.gientech.ragindexservice.domain.model;

import com.baomidou.mybatisplus.annotation.*;
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
@TableName("folder_info")
public class FolderInfoDO implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", comment = "主键", isNull = false, isKey = true ,isAutoIncrement = true)
    private Long id;

    @Column(name = "name", comment = "文件夹名称", length = 512)
    private String name;

    @Column(name = "kb_id", comment = "知识库id")
    private Long kbId;

    @Column(name = "type", comment = "1:文档解析；2:FAQ抽取; 3;知识图谱 4:FAQ管理创建的文件夹或者从FAQ抽取复制的文件夹")
    private Integer type;

    @Column(name = "parent_id", comment = "父文件夹id")
    private Long parentId;

    @Column(name = "folder_label", comment = "文件夹标签", length = 512)
    private String folderLabel;

    @Column(name = "status", comment = "1：正常；-1：删除", defaultValue = "1")
    private Integer status;

    @Column(name = "gmt_create", comment = "创建时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtCreate;

    @Column(name = "gmt_modified", comment = "更新时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtModified;

    @Column(name = "create_by", comment = "创建人", length = 50)
    private String createBy;

    @Column(name = "update_by", comment = "更新人", length = 50)
    private String updateBy;

    @Column(name = "full_path", comment = "完整路径（包含结尾/)", length = 2000)
    private String fullPath;


}
