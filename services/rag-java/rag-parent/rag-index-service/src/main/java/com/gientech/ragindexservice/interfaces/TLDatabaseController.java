package com.gientech.ragindexservice.interfaces;

import cn.hutool.db.Entity;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.CommonResponse;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import com.gientech.ragcommon.index.request.QueryDataReq;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import com.gientech.ragindexservice.application.service.ModelInfoAppService;
import com.gientech.ragindexservice.application.service.TLDatabaseAppService;
import com.gientech.tools.database.application.remote.DatabaseRemoteService;
import com.gientech.ragcommon.index.dto.tools.TLDatabaseDTO;
import com.gientech.tools.database.interfaces.request.CancelFileReq;
import com.gientech.tools.database.interfaces.request.ParseAppendFileReq;
import com.gientech.tools.database.interfaces.request.ParseFileReq;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.codehaus.plexus.util.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.*;

@Tag(name = "数据库接入功能")
@RestController
@RequestMapping("/database/")
public class TLDatabaseController {
    @Autowired
    private TLDatabaseAppService tlDatabaseService;


    @Autowired
    private DatabaseRemoteService databaseRemoteService;

    @Autowired
    private ModelInfoAppService modelInfoAppService;


    @Value(("${remote.database-table-description.model}"))
    private String databaseTableDescriptionModelName;

    @Operation(summary = "同步数据表结构到es")
    @GetMapping("/syncTableSchema/{databaseId}/{tableName}")
    public Boolean syncTableSchema(@PathVariable("databaseId") Long databaseId,
                                   @PathVariable("tableName") String tableName) {
        return databaseRemoteService.syncTableSchema(databaseId, tableName);
    }

    @Operation(summary = "生成数据表描述（数据表）")
    @GetMapping("/genTableDescription/{tableId}")
    public String genTableDescription(@PathVariable("tableId") Long tableId) {
        ModelSimpDTO simpByModeName = modelInfoAppService.getSimpByModeName(databaseTableDescriptionModelName);
        if (Objects.isNull(simpByModeName)) {
            throw new ApplicationException(ErrCodeEnum.MODEL_NOT_AVAILABLE.getErrCode(), databaseTableDescriptionModelName);
        }
        return databaseRemoteService.genTableDescription(tableId, simpByModeName);
    }

    @Operation(summary = "生成并更新数据表描述（数据表）")
    @GetMapping("/genUpdateTableDescription/{databaseId}/{tableName}")
    public Boolean genUpdateTableDescription(@PathVariable("databaseId") Long databaseId,
                                             @PathVariable("tableName") String tableName) {
        ModelSimpDTO simpByModeName = modelInfoAppService.getSimpByModeName(databaseTableDescriptionModelName);
        if (Objects.isNull(simpByModeName)) {
            throw new ApplicationException(ErrCodeEnum.MODEL_NOT_AVAILABLE.getErrCode(), databaseTableDescriptionModelName);
        }
        return databaseRemoteService.genUpdateTableDescription(databaseId, tableName, simpByModeName);
    }

    @Operation(summary = "数据库列表")
    @GetMapping("/queryPageDBList")
    public Page<TLDatabaseDTO> queryPageDBList(@RequestParam(value = "pageNo", required = false) Long pageNo,
                                               @RequestParam(value = "pageSize", required = false) Long pageSize,
                                               @RequestParam(value = "fuzzyWord", required = false) String fuzzyWord) {
        String userName = UserContext.getUser().getUserName();
        if (StringUtils.isBlank(userName)) {
            Page<TLDatabaseDTO> rst = new Page<>(pageNo, pageSize);
            rst.setRecords(List.of());
            return rst;
        }
        return tlDatabaseService.pageDBList(pageNo, pageSize, fuzzyWord, UserContext.getUser().getUserName(), Boolean.TRUE);
    }

    @Operation(summary = "共享数据库列表")
    @GetMapping("/queryShareDBList")
    @OperationLog(operateType = "查询共享数据库列表")
    public Page<TLDatabaseDTO> queryShareDBList(@RequestParam(value = "pageNo", required = false) Long pageNo,
                                                @RequestParam(value = "pageSize", required = false) Long pageSize,
                                                @RequestParam(value = "fuzzyWord", required = false) String fuzzyWord) {
        return tlDatabaseService.shareDBList(pageNo, pageSize, fuzzyWord);
    }


    @Operation(summary = "获取用户的所有数据库（我的+共享）")
    @GetMapping("/queryAllDBList")
    @OperationLog(operateType = "获取用户所有有权限的数据库")
    public Set<TLDatabaseDTO> searchAllDB(@RequestParam(value = "fuzzyWord", required = false) String fuzzyWord) {
        return tlDatabaseService.searchAllDB(fuzzyWord);
    }


    @Operation(summary = "根据id获取数据库")
    @GetMapping("/{databaseId}")
    @OperationLog(operateType = "根据id获取数据库")
    public TLDatabaseDTO queryDB(@PathVariable("databaseId") Long databaseId) {
        return tlDatabaseService.findById(databaseId);
    }

    @Operation(summary = "获取数据库的创建者")
    @GetMapping("/queryDatabaseCreator/{databaseId}")
    public CommonResponse<String> queryDatabaseCreator(@PathVariable("databaseId") Long databaseId) {
        String creator = tlDatabaseService.queryDatabaseCreator(databaseId);
        return CommonResponse.success(creator);
    }

    @Operation(summary = "执行sql查询数据")
    @PostMapping("/queryData")
    public List<Entity> queryData(@RequestBody QueryDataReq executeSqlReq) {
        return tlDatabaseService.queryData(executeSqlReq);
    }

    @Operation(summary = "数据表-文件上传，返回文件编号")
    @PostMapping("/dataTable/uploadFile")
    public Long uploadFile(
            @RequestParam("databaseId") Long databaseId,
            @RequestParam(name = "tableId", required = false) Long tableId,
            @RequestParam(value = "tableFile") MultipartFile tableFile) {
        return tlDatabaseService.uploadFile(databaseId, tableId, tableFile);
    }

    @Operation(summary = "数据表-取消文件上传")
    @PostMapping("/dataTable/cancelUploadFile")
    public Boolean cancelUploadFile(@RequestBody CancelFileReq cancelFileReq) {
        return tlDatabaseService.cancelUploadFile(cancelFileReq.getFileIds());
    }

    @Operation(summary = "数据表-新增文件解析")
    @PostMapping("/dataTable/parseFiles")
    public Boolean parseFiles(@RequestBody ParseFileReq parseFileReq) {
        List<Long> fileIds = parseFileReq.getFileIds();

        Map<Long, String> tableDescriptionMap = parseFileReq.getTableDescriptionMap();
        if (tableDescriptionMap == null) {
            tableDescriptionMap = new HashMap<>();
        }

        Boolean isGenDescription = parseFileReq.getIsGenDescription();
        if (isGenDescription == null) {
            isGenDescription = false;
        }
        tlDatabaseService.parseFiles(fileIds, tableDescriptionMap, isGenDescription);
        return true;
    }

    @Operation(summary = "数据表-追加文件解析")
    @PostMapping("/dataTable/parseAppendFiles")
    public Boolean parseAppendFiles(@RequestBody ParseAppendFileReq parseAppendFileReq) {
        List<Long> fileIds = parseAppendFileReq.getFileIds();
        Long tableId = parseAppendFileReq.getTableId();
        tlDatabaseService.parseAppendFiles(fileIds, tableId);
        return true;
    }

    @Operation(summary = "数据表-重新解析某个文件")
    @PostMapping("/dataTable/reParseFile/{fileId}")
    public Boolean reParseFile(@PathVariable(name = "fileId") Long fileId) {
        tlDatabaseService.reParseFile(fileId);
        return true;
    }
}
