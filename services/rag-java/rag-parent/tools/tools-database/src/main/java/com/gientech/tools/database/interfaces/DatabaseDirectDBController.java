package com.gientech.tools.database.interfaces;

import cn.hutool.core.bean.BeanUtil;
import com.gientech.tools.database.application.DatabaseDirectDBService;
import com.gientech.tools.database.application.remote.DatabaseRemoteService;
import com.gientech.tools.database.domain.entity.TLDatabase;
import com.gientech.ragcommon.index.dto.tools.TLDatabaseDTO;
import com.gientech.ragcommon.index.dto.tools.TLTableDataDto;
import com.gientech.tools.database.interfaces.dto.TLTableDto;
import com.gientech.tools.database.interfaces.request.SaveDirectDBReq;
import com.gientech.tools.database.interfaces.request.TestDBConnectReq;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Tag(name = "直连数据库功能")
@RestController
@RequestMapping("/database/directDB")
public class DatabaseDirectDBController {
    @Autowired
    private DatabaseDirectDBService databaseDirectDBService;

    @Autowired
    private DatabaseRemoteService databaseRemoteService;

    @Operation(summary = "测试数据库连接")
    @PostMapping("/testConnect")
    public Boolean testConnect(@RequestBody @Validated TestDBConnectReq testDBConnectReq) {
        TLDatabase dbDatabase = BeanUtil.copyProperties(testDBConnectReq, TLDatabase.class);
        return databaseDirectDBService.testConnect(dbDatabase);
    }

    @Operation(summary = "保存数据库信息")
    @PostMapping("/saveDBInfo")
    public TLDatabaseDTO saveDBInfo(@RequestBody @Validated SaveDirectDBReq saveDirectDBReq) {
        TLDatabase dbDatabase = BeanUtil.copyProperties(saveDirectDBReq, TLDatabase.class);
        Long databaseId = databaseDirectDBService.saveDBInfo(dbDatabase);
        return databaseDirectDBService.queryDBInfo(databaseId);
    }

    @Operation(summary = "手动同步表结构到ES")
    @GetMapping("/syncSchema/{databaseId}")
    public Boolean syncSchema(@PathVariable("databaseId") Long databaseId) {
        databaseRemoteService.batchSyncTableSchema(databaseId);
        return true;
    }

    @Operation(summary = "数据库信息查询")
    @GetMapping("/queryDBInfo/{databaseId}")
    public TLDatabaseDTO queryDBInfo(@PathVariable("databaseId") Long databaseId) {
        return databaseDirectDBService.queryDBInfo(databaseId);
    }

    @Operation(summary = "查询表清单")
    @GetMapping("/queryTableList/{databaseId}")
    public List<TLTableDto> queryTableList(@PathVariable("databaseId") Long databaseId) {
        return databaseDirectDBService.pageTableList(databaseId);
    }

    @Operation(summary = "查询表元信息")
    @GetMapping("/queryTableMeta/{databaseId}/{tableName}")
    public TLTableDto queryTableMeta(@PathVariable("databaseId") Long databaseId,
                                           @PathVariable("tableName") String tableName) {
        return databaseDirectDBService.queryTableMeta(databaseId, tableName);
    }

    @Operation(summary = "查询表数据")
    @GetMapping("/queryTableData/{databaseId}/{tableName}")
    public TLTableDataDto queryTableData(@PathVariable("databaseId") Long databaseId,
                                         @PathVariable("tableName") String tableName,
                                         @RequestParam(value = "pageNo", required = false, defaultValue = "1") Long pageNo,
                                         @RequestParam(value = "pageSize", required = false, defaultValue = "100") Long pageSize) {
        return databaseDirectDBService.pageTableData(databaseId, tableName, pageNo, pageSize);
    }

    @Operation(summary = "通过id删除数据库配置")
    @DeleteMapping("/deleteDB/{databaseId}")
    public Boolean deleteDB(@PathVariable("databaseId") Long databaseId) {
        return databaseDirectDBService.deleteDB(databaseId);
    }
}
