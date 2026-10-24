package com.gientech.ragindexservice.interfaces;

import com.gientech.ragcommon.index.request.TaskReq;
import com.gientech.ragindexservice.application.service.FileParseTaskAppService;
import io.swagger.v3.oas.annotations.Operation;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/parseTask")
public class FileParseTaskController {

    @Autowired
    private FileParseTaskAppService fileParseTaskAppService;

    @Operation(summary = "执行解析任务任务(定时任务调度)")
    @PostMapping("/execTask")
    public Boolean execTask() {
        return fileParseTaskAppService.execTask();
    }

    @Operation(summary = "任务更新回调函数")
    @PostMapping("/callback")
    public Boolean taskCallback(@RequestBody TaskReq taskReq) {
        return fileParseTaskAppService.taskCallback(taskReq);
    }
}
