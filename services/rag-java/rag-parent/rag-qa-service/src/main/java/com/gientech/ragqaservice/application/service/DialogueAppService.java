package com.gientech.ragqaservice.application.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.qa.dto.DialogDTO;
import com.gientech.ragcommon.qa.request.DialogCreateRequest;
import com.gientech.ragcommon.qa.request.DialogQueryRequest;
import com.gientech.ragcommon.qa.request.DialogRenameRequest;

public interface DialogueAppService {

    DialogDTO create(DialogCreateRequest createRequest);

    DialogDTO reName(DialogRenameRequest renameRequest);

    Boolean delete(String sessionId);

    DialogDTO getDialogBySessionId(String sessionId);

    Page<DialogDTO> list(DialogQueryRequest queryRequest);

    Boolean updateQaFiles(String queryId, String filePaths);
}
