package com.gientech.ragcommon.index.request;

import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.List;

@Schema(name = "解析任务更新参数")
@Data
public class TaskReq {

    @JsonProperty("success")
    public Boolean success;

    @JsonProperty("msg")
    public String msg;

    @JsonProperty("task_id")
    public Long taskId;

    @JsonProperty("task_statuses")
    public List<TaskStatus> taskStatuses;

    @Data
    public static class TaskStatus {
        @JsonProperty("file_path")
        public String filePath;

        @JsonProperty("file_id")
        public Long fileId;

        @JsonProperty("success")
        public boolean success;

        @JsonProperty("fail_reason")
        public String failReason;

        @JsonProperty("revise_date")
        public String reviseDate;
    }

}
