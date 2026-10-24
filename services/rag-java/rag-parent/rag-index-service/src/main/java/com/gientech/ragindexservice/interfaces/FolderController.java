package com.gientech.ragindexservice.interfaces;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.global.CommonResponse;
import com.gientech.ragcommon.index.dto.FolderDTO;
import com.gientech.ragcommon.index.dto.FolderInfoDTO;
import com.gientech.ragcommon.index.dto.SaveFolderInfoReq;
import com.gientech.ragcommon.index.request.*;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import com.gientech.ragindexservice.application.service.FolderInfoAppService;
import com.gientech.ragindexservice.infrastructure.FolderTreeBuilder;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Tag(name = "知识库文件夹")
@RestController
@RequestMapping("/folder")
public class FolderController {

    @Autowired
    private FolderInfoAppService folderInfoAppService;

    @Operation(summary = "分页查询")
    @GetMapping("/list")
    public Page<FolderInfoDTO> list(
            @RequestParam(value = "pageNo", required = false) Long pageNo,
            @RequestParam(value = "pageSize", required = false) Long pageSize) {
        return folderInfoAppService.list(pageNo, pageSize);
    }

    @Operation(summary = "通过知识库id查询文件目录(有层级关系)")
    @GetMapping("/leve/list")
    public List<FolderInfoDTO> leveList(@RequestParam("kbIds") List<Long> kbIds) {
        return folderInfoAppService.leveList(kbIds);
    }

    @Operation(summary = "通过id查询数据")
    @GetMapping("/id")
    public FolderInfoDTO queryFolderInfo(@RequestParam("id") Long id) {
        return folderInfoAppService.findById(id);
    }

    @Operation(summary = "保存")
    @PostMapping("/save")
    @OperationLog(operateType = "创建文件夹")
    public Boolean saveFolderInfo(@RequestBody @Validated SaveFolderInfoReq folderInfoReq) {
        return folderInfoAppService.save(folderInfoReq);
    }

    @Operation(summary = "重命名")
    @PutMapping("/rename")
    @OperationLog(operateType = "重命名文件夹")
    public Boolean rename(@RequestBody @Validated UpdateFolderInfoReq updateLogTestReq) {
        return folderInfoAppService.rename(updateLogTestReq);
    }

    @Operation(summary = "通过id删除")
    @DeleteMapping("/delete")
    @OperationLog(operateType = "删除文件夹")
    public Boolean deleteFolderInfoById(@RequestParam("id") Long id) {
        return folderInfoAppService.deleteById(id);
    }

    @Operation(summary = "文件转移")
    @PostMapping("/file/transfer")
    public Boolean fileTransfer(@RequestBody @Validated FileTransferReq fileTransferReq) {
        return folderInfoAppService.fileTransfer(fileTransferReq);
    }

    @Operation(summary = "文件/文件夹转移")
    @PostMapping("/transfer")
    public Boolean transfer(@RequestBody @Validated TransferReq transferReq) {
        return folderInfoAppService.transfer(transferReq);
    }

    @Operation(summary = "文件/文件夹批量转移")
    @PostMapping("/transferBatch")
    public Boolean transferBatch(@RequestBody @Validated TransferBatchReq transferBatchReq) {
        return folderInfoAppService.transferBatch(transferBatchReq);
    }

    @Operation(summary = "文件夹添加标签")
    @PostMapping("/addLabel")
    public Boolean addLabel(@RequestParam("folderId") Long folderId,@RequestParam("label") String label) {
        return folderInfoAppService.addLabel(folderId,label);
    }

    @Operation(summary = "查询文档创建者")
    @GetMapping("/queryCreator")
    public CommonResponse<String> queryCreator(@RequestParam(value = "id") Long id) {
        return CommonResponse.success(folderInfoAppService.queryCreator(id));
    }

    @Operation(summary = "查看指定kb下的文件夹")
    @PostMapping("/recursiveFolderByKb")
    public List<FolderInfoDTO> recursiveFolderByKb(@RequestBody @Valid QueryFolderReq queryFolderReq) {
        List<FolderInfoDTO> folderInfoDTOS = folderInfoAppService.recursiveFolderByKb(queryFolderReq);
        FolderTreeBuilder folderTreeBuilder = new FolderTreeBuilder();
        return folderTreeBuilder.buildTree(folderInfoDTOS);
    }

    @Operation(summary = "查看知识库下的文件夹以及文件")
    @GetMapping("/file/list")
    public List<FolderDTO> folderFileList(QueryFolderReq queryFolderReq) {
       return folderInfoAppService.folderFileList(queryFolderReq);
    }

}
