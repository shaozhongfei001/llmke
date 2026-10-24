package com.gientech.ragindexservice.interfaces;


import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.global.CommonResponse;
import com.gientech.ragcommon.index.dto.FileChunkDTO;
import com.gientech.ragcommon.index.dto.KnowledgeBaseFileDTO;
import com.gientech.ragcommon.index.request.*;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import com.gientech.ragindexservice.application.service.KnowledgeBaseListAppService;
import com.gientech.start.storage.exception.FileStorageException;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

@Tag(name = "知识库文件OpenAPI接口")
@RestController
@RequestMapping("/api/knowledgeBase/file")
public class KnowledgeBaseFileApiController {

    @Autowired
    private KnowledgeBaseListAppService knowledgeBaseListAppService;


    @Operation(summary = "批量上传文件(包含文件重复性校验、父文件、多版本)")
    @PostMapping("/uploadFileList")
    @OperationLog(operateType = "上传文档")
    public Object uploadFileList(@RequestParam("uploadFileParam") String uploadFileParam, @RequestParam("files") MultipartFile[] files) {
        return knowledgeBaseListAppService.uploadFileList(uploadFileParam, files);
    }

    @Operation(summary = "文件预检接口")
    @GetMapping("/precheck")
    public Set<String> precheck(@RequestParam("fileNameList") List<String> fileNameList) {
        return knowledgeBaseListAppService.precheck(fileNameList);
    }

    @Operation(summary = "批量获取文件详情")
    @GetMapping("/getById")
    @OperationLog(operateType = "查看文档详情")
    public List<KnowledgeBaseFileDTO> getById(@RequestParam("id") Long[] ids) {
        return knowledgeBaseListAppService.getByIds(ids);
    }

    @Operation(summary = "知识库文件列表")
    @GetMapping("/list")
    @OperationLog(operateType = "查看知识库文件列表")
    public LinkedHashSet<KnowledgeBaseFileDTO> fileList(KnowledgeBaseFileQueryReq req) {
        req.adjustIdAndIds();
        return knowledgeBaseListAppService.fileList(req);
    }


    @Operation(summary = "通过id删除文件")
    @DeleteMapping("/delete")
    @OperationLog(operateType = "删除文档")
    public Boolean delete(@Parameter(name = "id", description = "id", required = true) @RequestParam("id") Long id) {
        return knowledgeBaseListAppService.deleteById(id);
    }

    @Operation(summary = "通过id批量删除文件")
    @DeleteMapping("/deleteByIds")
    @OperationLog(operateType = "批量删除文档")
    public Boolean deleteByIds(@RequestParam("fileIds") List<Long> fileIds) {
        return knowledgeBaseListAppService.deleteByIds(fileIds);
    }

    @Operation(summary = "文件解析")
    @PostMapping("/filesParse")
    @OperationLog(operateType = "文档解析")
    public Boolean filesParse(@RequestBody FilesParseReq filesParseReq) {
        return knowledgeBaseListAppService.filesParseNew(filesParseReq);
    }

    @Operation(summary = "图解析")
    @PostMapping("/graphParse")
    @OperationLog(operateType = "图解析")
    public Boolean graphParse(@RequestBody FilesParseReq filesParseReq) {
        return knowledgeBaseListAppService.graphParse(filesParseReq);
    }

    @Operation(summary = "一键解析")
    @PostMapping("/filesAllParse")
    public Boolean filesAllParse(@RequestParam("kbId") Long kbId) {
        return knowledgeBaseListAppService.filesAllParse(kbId);
    }

    @Operation(summary = "文件的修订时间")
    @PutMapping("/filesReviseDate")
    public Boolean filesReviseDate(@RequestParam("fileId") Long fileId, @RequestParam("reviseDate") String reviseDate) {
        return knowledgeBaseListAppService.filesReviseDate(fileId, reviseDate);
    }

    @Operation(summary = "判断文件是否上传过，是否存在分片(-1 文件没有上传过; -2 文件已存在; 文件上传中断过，返回当前已经上传到的下标)")
    @GetMapping(value = "/check")
    public Integer checkCunkFile(
            @RequestParam("kbId") Long kbId,
            @RequestParam("fileName") String fileName,
            @RequestParam("fileMd5") String fileMd5){
        return knowledgeBaseListAppService.checkCunkFile(kbId, fileName, fileMd5);
    }

    @Operation(summary = "上传文件片段")
    @PostMapping(value = "/upload")
    public Boolean chunkUpload(
            @RequestParam("fileMd5") String fileMd5,
            @RequestParam("file") MultipartFile file) {
        return knowledgeBaseListAppService.chunkUpload(fileMd5, file);
    }

    @Operation(summary = "文件片段合并")
    @PostMapping(value = "/merge")
    public Boolean chunkMerge(@RequestBody FileMergeReq fileMergeReq) {
        return knowledgeBaseListAppService.chunkMerge(fileMergeReq);
    }

    @Operation(summary = "修改知识库文件状态")
    @PutMapping("/updateEnable")
    public Boolean updateEnable(@RequestBody FileEnableReq fileEnableReq) {
        return knowledgeBaseListAppService.updateEnable(fileEnableReq);
    }

    @Operation(summary = "查看文件解析状态")
    @GetMapping("/getFileStatusById")
    public Integer getFileStatusById(@RequestParam("fileId") Long fileId) {
        return knowledgeBaseListAppService.getFileStatusById(fileId);
    }

    @Operation(summary = "获取抽取状态")
    @GetMapping("/getFAQExtractStatusById")
    public Integer getFAQExtractStatusById(@RequestParam("fileId") Long fileId) {
        return knowledgeBaseListAppService.getFAQExtractStatusById(fileId);
    }

    @Operation(summary = "获取图解析状态 1 未解析；2 解析中 3 解析成功 4 解析失败")
    @GetMapping("/getGraphParseStatus")
    public Integer getGraphParseStatus(@RequestParam("fileId") Long fileId) {
        return knowledgeBaseListAppService.getGraphParseStatus(fileId);
    }

    @Operation(summary = "上传解析后文件并返回文件的路径")
    @PostMapping("/uploadParsedFile")
    @OperationLog(operateType = "上传文档")
    public KnowledgeBaseFileDTO uploadFile(
            @RequestParam("kbId") Long kbId,
            @RequestParam("fileId") Long fileId,
            @RequestParam("userId") String userId,
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "imagesFiles", required = false) List<MultipartFile> imagesFiles,
            @RequestParam(value = "tableFiles", required = false) List<MultipartFile> tableFiles,
            @RequestParam(value = "isOverwrite", defaultValue = "true", required = false) boolean isOverwrite) {
        return knowledgeBaseListAppService.uploadFile(kbId, fileId, userId, file, imagesFiles,tableFiles,isOverwrite);
    }

    @Operation(summary = "FAQ抽取")
    @PostMapping("/extractFQA")
    @OperationLog(operateType = "FAQ抽取")
    public Boolean extractFQA(@RequestBody FilesParseReq filesParseReq) {
//        return knowledgeBaseListAppService.filesExtractFAQNew(filesParseReq);
        return knowledgeBaseListAppService.reExtractFQA(filesParseReq);
    }

    @Operation(summary = "FAQ一键抽取")
    @PostMapping("/extractAllFQA")
    public Boolean extractAllFQA(@RequestParam("kbId") Long kbId) {
        return knowledgeBaseListAppService.extractAllFQA(kbId);
    }

    @Operation(summary = "FAQ重新抽取")
    @PostMapping("/reExtractFQA")
    @OperationLog(operateType = "FAQ重新抽取")
    public Boolean reExtractFQA(@RequestBody FilesParseReq filesParseReq) {
        return knowledgeBaseListAppService.reExtractFQA(filesParseReq);
    }

    @Operation(summary = "查看文件chunk")
    @GetMapping("/getFileChunks")
    @OperationLog(operateType = "查看文档chunk")
    public Page<FileChunkDTO> getFileChunks(@RequestParam("kbId") Long kbId, @RequestParam("docId") Long docId, @RequestParam("pageNo") Integer pageNo, @RequestParam("pageSize") Integer pageSize) {
        return knowledgeBaseListAppService.getFileChunksByPage(kbId, docId, pageNo, pageSize);
    }

    @Operation(summary = "通过知识库名和文件名查询文本块")
    @GetMapping("/getKbFileChunks")
    @OperationLog(operateType = "通过知识库名和文件名查询文本块")
    public List<FileChunkDTO> getKbFileChunks(@RequestParam("kbName") String kbName, @RequestParam("fileName") String fileName, @RequestParam("pageNo") Integer pageNo, @RequestParam("pageSize") Integer pageSize) {
        return knowledgeBaseListAppService.getKbFileChunks(kbName, fileName, pageNo, pageSize);
    }

    @Operation(summary = "文本chunk关联图片chunk调整")
    @PutMapping("/image/chunkChange")
    public Boolean chunkChange(@RequestBody @Validated ChunkChangeReq chunkChangeReq) {
        return knowledgeBaseListAppService.chunkChange(chunkChangeReq);
    }

    @Operation(summary = "从url列表导入文件(包含文件重复性校验、父文件、多版本)")
    @PostMapping("/importUrlList")
    public Object importUrlList(@RequestParam("importUrlListParam") String importUrlListParam) {
        return knowledgeBaseListAppService.importUrlList(importUrlListParam);
    }

    @Operation(summary = "更新文本块内容")
    @PutMapping("/updateChunk")
    public Boolean updateChunk(@RequestBody @Validated UpdateChunkReq updateChunkReq) {
        return knowledgeBaseListAppService.updateChunk(updateChunkReq);
    }

    @Operation(summary = "通过文本块id删除")
    @DeleteMapping("/deleteChunks")
    public Boolean deleteChunk(@RequestBody @Validated DeleteChunkReq deleteChunkReq) {
        return knowledgeBaseListAppService.deleteChunk(deleteChunkReq);
    }

    @Operation(summary = "查看文件")
    @GetMapping("/viewFile")
    public void viewFile(HttpServletResponse response, @RequestParam("fileUrl") String fileUrl) throws IOException {
        knowledgeBaseListAppService.viewFile(response, fileUrl);
    }

    @Operation(summary = "查询文档创建者")
    @GetMapping("/queryCreator")
    public CommonResponse<String> queryCreator(@RequestParam(value = "id") Long id) {
        return CommonResponse.success(knowledgeBaseListAppService.queryCreator(id));
    }

}
