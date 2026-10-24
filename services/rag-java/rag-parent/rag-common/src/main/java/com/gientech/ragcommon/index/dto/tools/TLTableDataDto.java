package com.gientech.ragcommon.index.dto.tools;

import cn.hutool.db.Entity;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Schema(name = "数据库")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TLTableDataDto {

    /** 编号 */
    @Schema(name = "id",description = "编号")
    private Long id;

    /**  表名 */
    @Schema(name = "tableName",description = "表名")
    private String tableName;

    /** 字段清单 */
    @Schema(name = "columns",description = "字段清单")
    private List<TLTableColumnDto> columns;

    @Schema(name = "dataList", description = "分页数据列表")
    private List<Entity> dataList;

    @Schema(name = "pageNo", description = "分页页码")
    private Integer pageNo;

    @Schema(name = "pageSize", description = "分页大小")
    private Integer pageSize;

    @Schema(name = "totalPage", description = "分页总页数")
    private Integer totalPage;


    @Schema(name = "totalData", description = "总数据量")
    private Integer totalData;

    @Schema(name = "permission",description = "数据权限 0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限")
    private Integer permission = 3;

    private Long fileId;
}
