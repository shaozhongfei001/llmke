package com.gientech.ragindexservice.domain.entity;

import com.gientech.ragcommon.auth.enums.BizTypeEnums;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Date;

@Builder
@AllArgsConstructor
@NoArgsConstructor
@Data
public class BizLabel {

    private static final long serialVersionUID = 1L;

    /**
     * id
     */
    private Long id;

    /**
     * 资源id
     */
    private Long targetId;

    /**
     * label
     */
    private String label;

    /**
     * 1:知识库;2:检索配置;3:模型;4:文件
     */
    private Integer bizType;

    /**
     * 创建时间
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

    /**
     * 是否删除 -1 删除  1 正常 默认值1
     */
    private Integer isDel;

    private String bizName;

    public String getIdStr() {
        if (BizTypeEnums.isFileType(bizType)) {
            return "file_" + id;
        }
        if (BizTypeEnums.isFolderType(bizType)) {
            return "folder_" + id;
        }
        return bizType + "_" + id;
    }

}
