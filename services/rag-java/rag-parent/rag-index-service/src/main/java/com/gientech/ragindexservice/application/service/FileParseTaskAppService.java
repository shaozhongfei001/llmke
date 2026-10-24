package com.gientech.ragindexservice.application.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.request.TaskReq;
import com.gientech.ragcommon.index.dto.FileParseTaskDTO;
import com.gientech.ragcommon.index.request.SaveFileParseTaskReq;
import com.gientech.ragcommon.index.request.UpdateFileParseTaskReq;

public interface FileParseTaskAppService {

    FileParseTaskDTO findById(Long id);

    Boolean save(SaveFileParseTaskReq fileParseTaskReq);

    Boolean updateById(UpdateFileParseTaskReq fileParseTaskReq);

    Page<FileParseTaskDTO> list(Long pageNo, Long pageSize);

    Boolean deleteById(Long id);

    Boolean execTask();

    Boolean taskCallback(TaskReq taskReq);

    Long getSequenceByFileId(Long fileId);

}
