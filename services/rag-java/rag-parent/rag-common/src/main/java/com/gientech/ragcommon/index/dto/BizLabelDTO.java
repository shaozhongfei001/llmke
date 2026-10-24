package com.gientech.ragcommon.index.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import com.fasterxml.jackson.annotation.JsonFormat;
import java.util.Date;
import java.util.Objects;

@Schema(name = "用户-数据权限关联")
@Data
public class BizLabelDTO {

    @Schema(name = "id",description = "id")
    private Long id;

    @Schema(name = "targetId",description = "资源id")
    private Long targetId;

    @Schema(name = "label",description = "label")
    private String label;

    @Schema(name = "bizType",description = "1:知识库;2:检索配置;3:模型;4:文件")
    private Integer bizType;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss",timezone = "GMT+8")
    @Schema(name = "gmtCreate",description = "创建时间")
    private Date gmtCreate;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss",timezone = "GMT+8")
    @Schema(name = "gmtModified",description = "更新时间")
    private Date gmtModified;

    @Schema(name = "createBy",description = "创建人")
    private String createBy;

    @Schema(name = "updateBy",description = "更新人")
    private String updateBy;

    @Schema(name = "isDel",description = "是否删除 -1 删除  1 正常 默认值1")
    private Integer isDel;

    private String bizName;

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        BizLabelDTO that = (BizLabelDTO) o;
        return Objects.equals(targetId, that.targetId) && Objects.equals(label, that.label) && Objects.equals(bizType, that.bizType) && Objects.equals(isDel, that.isDel);
    }

    @Override
    public int hashCode() {
        return Objects.hash(targetId, label, bizType, isDel);
    }
}
