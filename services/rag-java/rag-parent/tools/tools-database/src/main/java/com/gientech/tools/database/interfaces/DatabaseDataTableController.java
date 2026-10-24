package com.gientech.tools.database.interfaces;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.tools.database.application.DatabaseDataTableService;
import com.gientech.tools.database.domain.entity.TLDatabase;
import com.gientech.ragcommon.index.dto.tools.TLDatabaseDTO;
import com.gientech.ragcommon.index.dto.tools.TLTableDataDto;
import com.gientech.tools.database.interfaces.dto.TLTableDto;
import com.gientech.tools.database.interfaces.dto.TLTableFileDTO;
import com.gientech.tools.database.interfaces.request.SaveDataTableDBReq;
import com.gientech.tools.database.interfaces.request.UpdateColumnInfoReq;
import com.gientech.tools.database.interfaces.request.UpdateTableInfoReq;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayDeque;
import java.util.Map;

@Tag(name = "上传数据表功能")
@RestController
@RequestMapping("/database/dataTable")
public class DatabaseDataTableController {
    @Autowired
    private DatabaseDataTableService databaseDataTableService;

    @Operation(summary = "保存数据库信息")
    @PostMapping("/saveDBInfo")
    public TLDatabaseDTO saveDBInfo(@RequestBody @Validated SaveDataTableDBReq saveDataTableDBReq) {
        TLDatabase dbDatabase = BeanUtil.copyProperties(saveDataTableDBReq, TLDatabase.class);
        Long databaseId = databaseDataTableService.saveDBInfo(dbDatabase);
        TLDatabaseDTO tlDatabase = databaseDataTableService.queryDBInfo(databaseId);
        return tlDatabase;
    }

    @Operation(summary = "数据库信息查询")
    @GetMapping("/queryDBInfo/{databaseId}")
    public TLDatabaseDTO queryDBInfo(@PathVariable("databaseId") Long databaseId) {
        return databaseDataTableService.queryDBInfo(databaseId);
    }

    @Operation(summary = "查询表清单")
    @GetMapping("/queryTableList/{databaseId}")
    public Page<TLTableDto> queryTableList(@PathVariable("databaseId") Long databaseId,
                                           @RequestParam(value = "pageNo", required = false) Long pageNo,
                                           @RequestParam(value = "pageSize", required = false) Long pageSize) {
        return databaseDataTableService.pageTableList(databaseId, pageNo, pageSize);
    }

    @Operation(summary = "以文件为维度，展示数据表列表树")
    @GetMapping("/queryTableFileTreeList/{databaseId}")
    public ArrayDeque<TLTableFileDTO> queryTableFileTreeList(@PathVariable("databaseId") Long databaseId) {
        return databaseDataTableService.tableFileTreeList(databaseId);
    }

    @Operation(summary = "查询表元信息")
    @GetMapping("/queryTableMeta/{tableId}")
    public TLTableDto queryTableMeta(@PathVariable("tableId") Long tableId) {
        return databaseDataTableService.queryTableMeta(tableId);
    }

    @Operation(summary = "更新表信息：表名称、表描述")
    @PostMapping("/updateTableInfo")
    public Boolean updateTableInfo(@RequestBody @Validated UpdateTableInfoReq updateTableInfoReq) {
        Long tableId = updateTableInfoReq.getTableId();
        String businessName = updateTableInfoReq.getBusinessName();
        String description = updateTableInfoReq.getDescription();

        return databaseDataTableService.updateTableInfo(tableId, businessName, description);
    }

    @Operation(summary = "更新字段信息：字段描述、数据类型")
    @PostMapping("/updateColumnInfo")
    public Boolean updateColumnInfo(@RequestBody @Validated UpdateColumnInfoReq updateColumnInfoReq) {
        Long columnId = updateColumnInfoReq.getColumnId();
        String description = updateColumnInfoReq.getDescription();
        String dataType = updateColumnInfoReq.getDataType();

        return databaseDataTableService.updateColumnInfo(columnId, description, dataType);
    }


    @Operation(summary = "查询表数据")
    @GetMapping("/queryTableData/{tableId}")
    public TLTableDataDto queryTableData(@PathVariable("tableId") Long tableId,
                                         @RequestParam(value = "pageNo", required = false) Long pageNo,
                                         @RequestParam(value = "pageSize", required = false) Long pageSize) {
        return databaseDataTableService.pageTableData(tableId, pageNo, pageSize);
    }

    @Operation(summary = "以文件为维度，查询表数据")
    @GetMapping("/queryTableFileData/{fileId}")
    public TLTableDataDto queryTableFileData(@PathVariable("fileId") Long fileId,
                                             @RequestParam(value = "pageNo", required = false) Long pageNo,
                                             @RequestParam(value = "pageSize", required = false) Long pageSize) {
        return databaseDataTableService.pageTableFileData(fileId, pageNo, pageSize);
    }

    @Operation(summary = "根据tableId查询文件数据")
    @GetMapping("/queryTableFileData/{databaseId}/{tableId}")
    TLTableDataDto queryTableFileDataByTableId(
            @PathVariable("databaseId") Long databaseId,
            @PathVariable("tableId") Long tableId,
            @RequestParam(value = "pageNo", required = false) Long pageNo,
            @RequestParam(value = "pageSize", required = false) Long pageSize){
        return databaseDataTableService.pageTableFileDataByTableId(databaseId, tableId, pageNo, pageSize);
    }

    @Operation(summary = "通过tableId删除数据表")
    @DeleteMapping("/deleteTable/{tableId}")
    public Boolean deleteTable(@PathVariable("tableId") Long tableId) {
        return databaseDataTableService.deleteTable(tableId);
    }

    @Operation(summary = "删除数据表中fileId对应文件数据")
    @DeleteMapping("/deleteTableFileData/{fileId}")
    public Boolean deleteTableFileData(@PathVariable("fileId") Long fileId) {
        return databaseDataTableService.deleteTableFileData(fileId);
    }

    @Operation(summary = "通过databaseId删除数据库配置")
    @DeleteMapping("/deleteDB/{databaseId}")
    public Boolean deleteDB(@PathVariable("databaseId") Long databaseId) {
        return databaseDataTableService.deleteDB(databaseId);
    }

    @Operation(summary = "更新数据表的行数据")
    @PostMapping("/dataUpdateRow/{tableId}")
    public Boolean updateTableDataRow(
            @PathVariable("tableId") Long tableId,
            @RequestBody Map<String, String> rowMap) {
        return databaseDataTableService.dataUpdateRow(tableId, rowMap);
    }

    @Operation(summary = "删除数据表的行数据")
    @DeleteMapping("/dataDeleteRow/{tableId}/{rowId}")
    public Boolean dataDeleteRow(
            @PathVariable("tableId") Long tableId,
            @PathVariable("rowId") Long rowId) {
        return databaseDataTableService.dataDeleteRow(tableId, rowId);
    }
}
