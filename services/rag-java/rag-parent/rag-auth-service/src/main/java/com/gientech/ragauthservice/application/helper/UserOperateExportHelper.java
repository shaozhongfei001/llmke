package com.gientech.ragauthservice.application.helper;

import com.gientech.ragcommon.auth.dto.UserOperateExportDTO;
import com.gientech.start.easyexcel.template.BaseExcelService;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
public class UserOperateExportHelper extends BaseExcelService<UserOperateExportDTO>  {

    @Override
    protected void handlerSuccessList(List<UserOperateExportDTO> list, Object... objects) {

    }

    @Override
    protected void handlerFailList(List<UserOperateExportDTO> list, Object... objects) {

    }
}
