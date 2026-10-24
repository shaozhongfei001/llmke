package com.gientech.ragqaservice.interfaces;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import com.gientech.ragcommon.qa.dto.DialogDTO;
import com.gientech.ragcommon.qa.request.DialogCreateRequest;
import com.gientech.ragcommon.qa.request.DialogRenameRequest;
import com.gientech.ragcommon.qa.request.DialogQueryRequest;
import com.gientech.ragqaservice.application.service.DialogueAppService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

/**
 * <p>
 * 对话 前端控制器
 * </p>
 *
 * @author wudf
 * @since 2024-05-08
 */
@Tag(name = "对话接口")
@RestController
@RequestMapping("/dialogue")
public class DialogueController {

    @Autowired
    private DialogueAppService dialogueAppService;

    @PostMapping(value = "create")
    @Operation(summary = "创建对话")
    @OperationLog(operateType = "创建对话")
    public DialogDTO create(@RequestBody @Validated DialogCreateRequest createRequest)  {
        return dialogueAppService.create(createRequest);
    }

    @PostMapping(value = "reName")
    @Operation(summary =  "重命名对话")
    @OperationLog(operateType = "重命名对话")
    public DialogDTO reName(@RequestBody DialogRenameRequest renameRequest) {
        return dialogueAppService.reName(renameRequest);
    }

    @DeleteMapping(value = "delete")
    @Operation(summary = "删除对话")
    @OperationLog(operateType = "删除对话")
    public Boolean delete(@RequestParam("sessionId") String sessionId) {
        return dialogueAppService.delete(sessionId);
    }

    @GetMapping(value = "getDialogBySessionId")
    @Operation(summary = "根据对话ID获取对话")
    @OperationLog(operateType = "查看对话详情")
    public DialogDTO getDialogBySessionId(@RequestParam("sessionId") String sessionId) {
        return dialogueAppService.getDialogBySessionId(sessionId);
    }

    @GetMapping(value = "list")
    @Operation(summary = "获取对话列表")
    @OperationLog(operateType = "查看对话列表")
    public Page<DialogDTO> list(DialogQueryRequest queryRequest)  {
        return dialogueAppService.list(queryRequest);
    }

    @PutMapping(value = "updateQaFiles")
    @Operation(summary = "更新文档上问答中答案最新的文档")
    @OperationLog(operateType = "更新文档上问答中答案最新的文档")
    public Boolean updateQaFiles(@RequestParam("queryId") String queryId,@RequestParam("filePaths") String filePaths)  {
        return dialogueAppService.updateQaFiles(queryId,filePaths);
    }


}
