package com.gientech.ragcommon.index.dto.tools;

import com.alibaba.fastjson2.annotation.JSONField;
import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Date;
import java.util.List;

@Schema(name = "数据库")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TLTableDto {
    /** 编号 */
    @Schema(name = "id",description = "编号")
    @JSONField(name = "id")
    private Long id ;

    /** 数据库编号 */
    @Schema(name = "databaseId", description = "数据库编号")
    @JSONField(name = "database_id")
    private Long databaseId ;

    /** 数据库名称 */
    @Schema(name = "databaseName", description = "数据库名称")
    @JSONField(name = "database_name")
    private String databaseName ;

    /** 数据库描述 */
    @Schema(name = "databaseDescription", description = "数据库描述")
    @JSONField(name = "database_description")
    private String databaseDescription ;

    /** 业务表名 */
    @Schema(name = "businessName", description = "业务表名")
    @JSONField(name = "business_name")
    private String businessName ;

    /** 物理表名 */
    @Schema(name = "physicalName", description = "物理表名")
    @JSONField(name = "physical_name")
    private String physicalName ;

    /** 表描述 */
    @Schema(name = "description", description = "表描述")
    @JSONField(name = "description")
    private String description ;

    /** 列数量 */
    @Schema(name = "columnCount", description = "列数量")
    @JSONField(name = "column_count")
    private Integer columnCount ;

    /** 行数量 */
    @Schema(name = "rowCount", description = "行数量")
    @JSONField(name = "row_count")
    private Long rowCount ;

    /** 解析状态 */
    @Schema(name = "parseStatus", description = "解析状态")
    @JSONField(name = "parse_status")
    private String parseStatus;

    @JSONField(name = "columns")
    List<TLTableColumnDto> columns;

    @Schema(name = "permission",description = "数据权限 0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限")
    private Integer permission;

    /** 创建时间 */
    @Schema(name = "gmt_create", description = "创建时间")
    @JSONField(name = "gmt_create")
    private Date gmtCreate ;

    /** 更新时间 */
    @Schema(name = "gmt_modified", description = "更新时间")
    @JSONField(name = "gmt_modified")
    private Date gmtModified ;

    /** 创建人 */
    @Schema(name = "create_by", description = "创建人")
    @JSONField(name = "create_by")
    private String createBy ;

    /** 更新人 */
    @Schema(name = "update_by", description = "更新人")
    @JSONField(name = "update_by")
    private String updateBy ;

    @JsonProperty("isGenDescription")
    private Boolean isGenDesc;

    @JsonProperty("generateDescriptionErrMsg")
    private String genDescErrMsg;

    @JsonProperty("generateDescriptionStatus")
    private String genDescStatus;

}
