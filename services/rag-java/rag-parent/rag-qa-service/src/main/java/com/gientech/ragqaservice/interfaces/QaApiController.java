package com.gientech.ragqaservice.interfaces;

import com.alibaba.fastjson2.JSONObject;
import com.gientech.ragcommon.index.dto.FileStatusDTO;
import com.gientech.ragcommon.index.dto.KnowledgeBaseFileDTO;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import com.gientech.ragcommon.qa.dto.DialogDTO;
import com.gientech.ragcommon.qa.dto.ReplyDTO;
import com.gientech.ragcommon.qa.request.AiRequest;
import com.gientech.ragcommon.qa.request.DialogCreateRequest;
import com.gientech.ragcommon.qa.request.FeedbackReq;
import com.gientech.ragqaservice.application.remote.KbClient;
import com.gientech.ragqaservice.application.service.AiService;
import com.gientech.ragqaservice.application.service.DialogueAppService;
import com.gientech.ragqaservice.application.service.FeedbackAppService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import reactor.core.publisher.Flux;

import java.util.List;

@Tag(name = "问答相关接口")
@RestController
@RequestMapping("/apis")
public class QaApiController {

    @Autowired
    private AiService aiService;

    @Autowired
    private FeedbackAppService feedbackAppService;

    @Autowired
    private DialogueAppService dialogueAppService;

    @Autowired
    private KbClient kbClient;

    @Operation(summary = "检索召回接口和模型推理接口，返回结果未拼接")
    @PostMapping(value = "/question_re", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    @OperationLog(operateType = "用户问答")
    public Flux<ReplyDTO> questionRe(@Validated @RequestBody AiRequest aiRequest) {
        return aiService.questionRe(aiRequest);
    }

    @GetMapping("/que/list")
    @Operation(summary = "问题列表")
    @OperationLog(operateType = "查看问题列")
    public List<JSONObject> queList() {
        return feedbackAppService.queList();
    }

    @PostMapping(value = "create")
    @Operation(summary = "创建对话")
    @OperationLog(operateType = "创建对话")
    public DialogDTO create(@RequestBody @Validated DialogCreateRequest createRequest)  {
        return dialogueAppService.create(createRequest);
    }

    @PostMapping("/feedback")
    @Operation(summary = "反馈")
    @OperationLog(operateType = "用户反馈")
    public Boolean feedback(@RequestBody @Validated FeedbackReq feedbackReq){
        return feedbackAppService.feedback(feedbackReq);
    }

    @DeleteMapping("/cancel")
    @Operation(summary = "取消反馈")
    @OperationLog(operateType = "用户取消反馈")
    public Boolean cancel(@RequestParam(value = "queryId") String queryId){
        return feedbackAppService.cancel(queryId);
    }

    @Operation(summary = "批量上传文件(文档上传问答)")
    @PostMapping("/uploadFiles")
    @OperationLog(operateType = "上传文档")
    public Object docUploadFile(@RequestParam(value = "sessionId") String sessionId, @RequestParam("uids") List<String> uids, @RequestParam("files") MultipartFile[] files) {
        return kbClient.docUploadFile(sessionId, uids, files);
    }

    @Operation(summary = "判断文件是否上传过")
    @GetMapping("/exist")
    @OperationLog(operateType = "上传文档")
    public Boolean exist(
            @RequestParam("kbName") String kbName,
            @RequestParam("fileName") String fileName,
            @RequestParam(value = "type", defaultValue = "4", required = false) Integer type) {
        return kbClient.exist(kbName, fileName, type);
    }

    @Operation(summary = "通过uid查看文件解析状态")
    @GetMapping("/getFileStatusByUids")
    public List<FileStatusDTO> getFileStatusByUid(@RequestParam("uids") List<String> uids) {
        return kbClient.getFileStatusByUid(uids);
    }

    @Operation(summary = "通过uid删除")
    @DeleteMapping("/deleteByUid")
    public List<KnowledgeBaseFileDTO> deleteByUid(@RequestParam(value = "queryId")String queryId, @RequestParam(value = "uid") String fileUid) {
        return kbClient.deleteByUid(queryId,fileUid);
    }
}
