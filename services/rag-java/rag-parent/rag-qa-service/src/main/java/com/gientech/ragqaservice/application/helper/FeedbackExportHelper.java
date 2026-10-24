package com.gientech.ragqaservice.application.helper;


import com.gientech.ragcommon.qa.dto.FeedbackExportDTO;
import com.gientech.start.easyexcel.template.BaseExcelService;
import org.springframework.stereotype.Component;
import java.util.List;

@Component
public class FeedbackExportHelper extends BaseExcelService<FeedbackExportDTO> {

    @Override
    protected void handlerSuccessList(List<FeedbackExportDTO> list, Object... objects) {

    }

    @Override
    protected void handlerFailList(List<FeedbackExportDTO> list, Object... objects) {

    }
}
