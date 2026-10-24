package com.gientech.tools.database.interfaces.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

@Schema(name = "数据表文件")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TLTableFileDTO {

    /** 文件编号 */
    @Schema(name = "fileId", description = "文件编号")
    private Long fileId ;

    /** 数据库编号 */
    @Schema(name = "database_id", description = "数据库编号")
    private Long databaseId ;

    /** 数据表编号 */
    @Schema(name = "table_id", description = "数据表编号")
    private Long tableId ;

    /** 原始文件名称 */
    @Schema(name = "original_filename", description = "原始文件名称")
    private String originalFilename;

    /** 列数量 */
    @Schema(name = "column_count", description = "列数量")
    private Integer columnCount ;

    /** 行数量 */
    @Schema(name = "row_count", description = "行数量")
    private Long rowCount ;

    /** 状态 */
    @Schema(name = "status", description = "解析状态")
    private String status ;

    /** 错误信息 */
    @Schema(name = "error_msg", description = "错误信息")
    private String errorMsg ;

    /** 子节点列表 */
    @Schema(name = "children", description = "子节点列表")
    private ArrayDeque<TLTableFileDTO> children = new ArrayDeque<>();;

    /** 表结构信息 */
    @Schema(name = "table_meta", description = "表结构信息")
    private TLTableDto tableMeta;

    @Schema(name = "permission",description = "数据权限 0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限")
    private Integer permission;

    /** 创建时间 */
    @Schema(name = "gmt_create", description = "创建时间")
    private Date gmtCreate ;

    /** 更新时间 */
    @Schema(name = "gmt_modified", description = "更新时间")
    private Date gmtModified ;

    /** 创建人 */
    @Schema(name = "create_by", description = "创建人")
    private String createBy ;

    /** 更新人 */
    @Schema(name = "update_by", description = "更新人")
    private String updateBy ;

    // 添加子节点
    public void addChild(TLTableFileDTO child) {
        children.push(child);
    }


}
