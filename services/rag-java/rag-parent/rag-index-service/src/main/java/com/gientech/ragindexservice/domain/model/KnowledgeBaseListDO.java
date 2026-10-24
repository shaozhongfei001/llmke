package com.gientech.ragindexservice.domain.model;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.gientech.ragcommon.index.enmus.TempStatusEnums;
import com.gientech.ragcommon.infrastructure.typehandler.StringListTypeHandler;
import com.gitee.sunchenbin.mybatis.actable.annotation.Column;
import com.gitee.sunchenbin.mybatis.actable.annotation.TableComment;
import com.gitee.sunchenbin.mybatis.actable.constants.MySqlTypeConstant;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.Date;
import java.util.List;

@Builder
@Data
@NoArgsConstructor
@AllArgsConstructor
@TableName("knowledge_base_list")
@TableComment("知识库明细")
public class KnowledgeBaseListDO implements Serializable {

    private static final long serialVersionUID = 1L;

    @TableId(value = "id", type = IdType.AUTO)
    @Column(name = "id", isNull = false, comment = "主键", isKey = true, isAutoIncrement = true)
    private Long id;

    @Column(name = "kb_id", isNull = false, comment = "知识库id")
    private Long kbId;

    @Column(name = "file_id", comment = "minIO文件的id", length = 64)
    private String fileId;

    @Column(name = "file_name", comment = "文件id", length = 128)
    private String fileName;

    @Column(name = "file_size", comment = "文件大小")
    private String fileSize;

    @Column(name = "file_path", comment = "路径", length = 256)
    private String filePath;

    @Column(name = "full_text_path", comment = "全文txt路径", length = 256)
    private String fullTextPath;

    @Column(name = "status", defaultValue = "1", comment = "状态 0:删除 1:正常 2:解析中，3:解析成功 4: 解析失败")
    private Integer status;

    @Column(name = "is_enable", defaultValue = "1", comment = "0:禁用;1启用")
    private Integer isEnable;

    @Column(name = "create_by", comment = "创建人", length = 30)
    private String createBy;

    @Column(name = "gmt_create", comment = "创建时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtCreate;

    @Column(name = "modify_by", comment = "修改人", length = 30)
    private String modifyBy;

    @Column(name = "gmt_modified", comment = "修改时间", type = MySqlTypeConstant.DATETIME)
    private Date gmtModified;

    @Column(name = "parsed_file_path", length = 255)
    private String parsedFilePath;

    @Column(name = "parse_type", defaultValue = "1", comment = "1 文件解析；2 FAQ解析 3 图解析；4 文档上传问答; 5 从文件解析复制的文件或者FAQ导入的问答对文件; 10 文件解析&faq抽取")
    private Integer parseType;

    @Column(name = "aq_count", defaultValue = "0", comment = "问答对数")
    private Integer aqCount;

    @Column(name = "faq_extract_status", defaultValue = "1", comment = "faq抽取状态 1 未抽取；2 抽取中 3 抽取成功 4 抽取失败")
    private Integer faqExtractStatus;

    @Column(name = "graph_parse_status", defaultValue = "1", comment = "图解析状态 1 未解析；2 解析中 3 解析成功 4 解析失败")
    private Integer graphParseStatus;

    @Column(name = "revise_date", comment = "修订实时间", length = 30)
    private String reviseDate;

    @Column(name = "parent_file_name", comment = "父文件名称", length = 127)
    private String parentFileName;

    @Column(name = "version", comment = "版本号", length = 16)
    private String version;

    @Column(name = "converted_file_path", comment = "转化后的文件路径", length = 512)
    private String convertedFilePath;

    @Column(name = "folder_id", comment = "文件夹id")
    private Long folderId;

    @Column(name = "source_url", comment = "文件url地址(从网页获取的文件)", length = 1000)
    private String sourceUrl;

    @Column(name = "chunking", comment = "文件是否chunk化", length = 1)
    private boolean chunking;

    @Column(name = "uid", comment = "文件的uid(uid是前端生成的,文档上传问答使用,通过uid来判断文件解析状态)", length = 128)
    private String uid;

    @Column(name = "temp_status", defaultValue = "2", comment = "1 临时文件,2 持久化文件 默认值是2")
    private Integer tempStatus = TempStatusEnums.PERSISTENCE.getCode();

    @TableField(exist = false)
    private Integer permission;

    @TableField(exist = false)
    private Integer isFolder;

    @Column(name = "group_id", comment = "文件集群组id，算法端根据文件内容生成", length = 512)
    private String groupId;

    @Column(name = "table_file_paths", comment = "表格解析后的文件路径", type = MySqlTypeConstant.LONGTEXT)
    private String tableFilePaths;

    // R12-FIX-DDL-02：原注解把 sourceId 误映射到 table_file_paths（与上一个字段重名），
    // 导致 MySQL 建表报 Duplicate column name 'table_file_paths'；该字段在全仓无任何读写使用，
    // 故标记为非持久化字段，保持 Java 字段与 API 不变。
    @com.baomidou.mybatisplus.annotation.TableField(exist = false)
    private Long sourceId;

    @Column(name = "pid", comment = "针对于FAQ管理，文件中有文件")
    private Long pid;

    @Column(name = "image_paths", type = MySqlTypeConstant.TEXT, comment = "图片解析路径")
    @TableField(typeHandler = StringListTypeHandler.class)
    private List<String> imagePaths;

    @Column(name = "chunk_type", comment = "切片策略", length = 32)
    private String chunkType;

}
