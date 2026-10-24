package com.gientech.ragindexservice.application.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.dto.FaqDTO;
import com.gientech.ragcommon.index.request.*;
import com.gientech.ragindexservice.domain.entity.FaqEsInfo;
import org.springframework.core.io.InputStreamResource;
import org.springframework.http.ResponseEntity;
import org.springframework.web.multipart.MultipartFile;
import java.util.List;
import java.util.Set;

public interface FAQAppService {

    ResponseEntity<InputStreamResource> downloadTemplate(String fileType) throws Exception;

    Boolean delete(FaqDeleteReq faqDeleteReq);

    Page<FaqDTO> listNew(FaqQueryReq queryReq);

    Page<FaqDTO> list(FaqQueryReq queryReq);

    Boolean uploadFiles(Long kbId,Long folderId,Long fileId, MultipartFile[] files);

    Boolean deleteFileById(List<Long> fileIds);

    Boolean saveOrUpdate(FaqSaveOrUpdateReq saveOrUpdateReq);

    List<FaqDTO> create(FaqSaveOrUpdateReq createReq);

    Boolean update(FaqSaveOrUpdateReq updateReq);

    Boolean similarQuestionAdd(SimilarQuestionReq similarQuestionAddReq);

    Boolean similarQuestionEdit(SimilarQuestionReq similarQuestionAddReq);

    Set<Set<FaqDTO>> changeStatus(FaqStatusUpdateReq faqStatusUpdateReq);

//    Set<Set<FaqDTO>> changeAllStatus(FaqAllStatusUpdateReq faqStatusUpdateReq);

    Set<Set<FaqDTO>> repeatCheck(Long kbId);

//    Boolean deleteAll(FaqDeleteReq faqDeleteReq);

    List<FaqDTO> polish(FaqPolishReq faqPolishReq);

    Boolean genSimilarQuestion(GenSimilarQuestionReq req);

    FaqDTO getFaqByRelatedPk(FaqQueryReq queryReq);

    Boolean similarQuestionDel(DelSimilarQuestionReq req);

    Page<FaqDTO> faqList(FaqQueryReq queryReq);

//    Boolean deleteFaq(FaqDelReq faqDelReq);

    Boolean transferFaq(FaqTransferReq faqTransferReq);

    Boolean deleteByPks(FaqDeleteReq faqDeleteReq);
}
