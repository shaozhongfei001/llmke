package com.gientech.ragindexservice.interfaces;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.dto.FaqDTO;
import com.gientech.ragcommon.index.request.*;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import com.gientech.ragindexservice.application.service.FAQAppService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.InputStreamResource;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Set;

/**
 * @Descrption: 问答对管理Controller接口
 * @Author:liutaiyun
 * @Date:2024/08/13 09:56
 **/
@Tag(name = "问答对(FAQ)")
@RestController
@RequestMapping("/faq")
public class FAQController {

    @Autowired
    private FAQAppService faqAppService;

    @Operation(summary = "新增")
    @PostMapping("/create")
    @OperationLog(operateType = "新增FAQ")
    public List<FaqDTO> create(@Validated @RequestBody FaqSaveOrUpdateReq createReq) {
        return faqAppService.create(createReq);
    }

    @Operation(summary = "更新")
    @PutMapping("/update")
    @OperationLog(operateType = "更新FAQ")
    public Boolean update(@Validated @RequestBody FaqSaveOrUpdateReq updateReq) {
        return faqAppService.update(updateReq);
    }

    @Operation(summary = "删除FAQ")
    @PostMapping("/delete")
    @OperationLog(operateType = "删除FAQ")
    public Boolean delete(@Validated @RequestBody FaqDeleteReq faqDeleteReq) {
        return faqAppService.delete(faqDeleteReq);
    }

    @Operation(summary = "通过pks删除FAQ")
    @DeleteMapping("/deleteByPks")
    @OperationLog(operateType = "通过pks删除FAQ")
    public Boolean deleteByPks(@Validated @RequestBody FaqDeleteReq faqDeleteReq) {
        return faqAppService.deleteByPks(faqDeleteReq);
    }

    @Operation(summary = "faq转移(包括文件，文件夹)")
    @PutMapping("/transferFaq")
    @OperationLog(operateType = "faq转移(包括文件，文件夹)")
    public Boolean transferFaq(@Validated @RequestBody FaqTransferReq faqTransferReq) {
        return faqAppService.transferFaq(faqTransferReq);
    }

    @Operation(summary = "问答列表数据")
    @GetMapping("/list")
    @OperationLog(operateType = "查询FAQ列表")
    public Page<FaqDTO> list(FaqQueryReq queryReq) {
        return faqAppService.faqList(queryReq);
    }

    @Operation(summary = "通过RelatedPk查询faq以及相似问")
    @GetMapping("/getFaqByRelatedPk")
    @OperationLog(operateType = "通过pk查询faq以及相似问")
    public FaqDTO getFaqByRelatedPk(FaqQueryReq queryReq) {
        return faqAppService.getFaqByRelatedPk(queryReq);
    }

    @Operation(summary = "模板下载")
    @GetMapping("/downloadTemplate")
    @OperationLog(operateType = "下载FAQ模版文件")
    public ResponseEntity<InputStreamResource> downloadTemplate(@RequestParam("fileType") String fileType) throws Exception {
        return faqAppService.downloadTemplate(fileType);
    }

    @Operation(summary = "上传文件")
    @PostMapping("/uploadFiles")
    @OperationLog(operateType = "上传文件")
    public Boolean uploadFiles(
            @RequestParam("kbId") Long kbId,
            @RequestParam(value = "folderId",required = false) Long folderId,
            @RequestParam(value = "fileId",required = false) Long fileId,
            @RequestParam("files") MultipartFile[] files) {
        return faqAppService.uploadFiles(kbId, folderId,fileId,files);
    }

    @Deprecated
    @Operation(summary = "通过id删除文件")
    @DeleteMapping("/deleteFileByIds")
    @OperationLog(operateType = "删除文件")
    public Boolean deleteFileById(@RequestParam("fileIds") List<Long> fileIds) {
        return faqAppService.deleteFileById(fileIds);
    }

    @Operation(summary = "新增相似问")
    @PostMapping("/similarQuestion/add")
    @OperationLog(operateType = "创建相似问")
    public Boolean similarQuestionAdd(@RequestBody @Validated SimilarQuestionReq similarQuestionAddReq) {
        return faqAppService.similarQuestionAdd(similarQuestionAddReq);
    }

    @Deprecated(since = "修改相似问")
    @Operation(summary = "修改相似问")
    @PutMapping("/similarQuestion/edit")
    @OperationLog(operateType = "编辑相似问")
    public Boolean similarQuestionEdit(@RequestBody @Validated SimilarQuestionReq similarQuestionAddReq) {
        return faqAppService.similarQuestionEdit(similarQuestionAddReq);
    }

    @Operation(summary = "faq启用/禁用")
    @PutMapping("/changeStatus")
    @OperationLog(operateType = "FAQ启用/禁用")
    public Set<Set<FaqDTO>> changeStatus(@RequestBody @Validated FaqStatusUpdateReq faqStatusUpdateReq) {
        return faqAppService.changeStatus(faqStatusUpdateReq);
    }

    @Operation(summary = "faq重复性校验")
    @GetMapping("/repeatCheck")
    @OperationLog(operateType = "FAQ重复性检测")
    public Set<Set<FaqDTO>> repeatCheck(@RequestParam("kbId") Long kbId) {
        return faqAppService.repeatCheck(kbId);
    }

    @Operation(summary = "FAQ润色")
    @PostMapping("/polish")
    public List<FaqDTO> polish(@RequestBody @Validated FaqPolishReq faqPolishReq) {
        return faqAppService.polish(faqPolishReq);
    }

    @Operation(summary = "生成相似问")
    @PutMapping("/gen/similarQuestion")
    @OperationLog(operateType = "生成相似问")
    public Boolean genSimilarQuestion(@RequestBody @Validated GenSimilarQuestionReq req) {
        return faqAppService.genSimilarQuestion(req);
    }

    @Operation(summary = "相似问删除")
    @DeleteMapping("/similarQuestion/delete")
    public Boolean similarQuestionDel(@RequestBody @Validated DelSimilarQuestionReq req) {
        return faqAppService.similarQuestionDel(req);
    }

}