package com.gientech.ragqaservice.interfaces;

import com.alibaba.fastjson2.JSONObject;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import com.gientech.ragcommon.qa.dto.FeedbackDTO;
import com.gientech.ragcommon.qa.request.FeedbackQueryReq;
import com.gientech.ragcommon.qa.request.FeedbackReq;
import com.gientech.ragqaservice.application.service.FeedbackAppService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import java.util.List;


/**
 * <p>
 * 反馈表 前端控制器
 * </p>
 *
 * @author wudf
 * @since 2024-07-18
 */
@Tag(name = "反馈")
@RestController
@RequestMapping("/feedback")
public class FeedbackController {

    @Autowired
    private FeedbackAppService feedbackAppService;

    @PostMapping("")
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

    @GetMapping("/que/list")
    @Operation(summary = "问题列表")
    @OperationLog(operateType = "查看问题列")
    public List<JSONObject> queList(){
        return feedbackAppService.queList();
    }

    @PostMapping("/list")
    @Operation(summary = "点踩列表")
    @OperationLog(operateType = "查看反馈列表")
    public Page<FeedbackDTO> list(@RequestBody FeedbackQueryReq feedbackQueryReq){
        return feedbackAppService.list(feedbackQueryReq);
    }

    @PostMapping(value = "/exportCsv")
    @Operation(summary = "数据导出")
    @OperationLog(operateType = "导出用户反馈")
    public void  exportCsv (@RequestBody FeedbackQueryReq feedbackQueryReq, HttpServletResponse response)  {
        feedbackAppService.exportCsv(feedbackQueryReq,response);
    }
}
