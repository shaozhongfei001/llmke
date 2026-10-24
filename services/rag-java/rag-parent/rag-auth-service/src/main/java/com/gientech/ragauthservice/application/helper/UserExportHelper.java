package com.gientech.ragauthservice.application.helper;

import com.gientech.ragcommon.auth.dto.UserExportDTO;

import com.gientech.start.easyexcel.template.BaseExcelService;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
public class UserExportHelper extends BaseExcelService<UserExportDTO> {

    @Override
    protected void handlerSuccessList(List<UserExportDTO> list, Object... objects) {

    }

    @Override
    protected void handlerFailList(List<UserExportDTO> list, Object... objects) {

    }
}
