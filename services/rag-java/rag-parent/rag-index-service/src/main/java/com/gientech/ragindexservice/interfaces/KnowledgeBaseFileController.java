package com.gientech.ragindexservice.interfaces;


import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.fasterxml.jackson.databind.JsonNode;
import com.gientech.ragcommon.index.dto.CollectDTO;
import com.gientech.ragcommon.index.dto.FileChunkDTO;
import com.gientech.ragcommon.index.dto.FileStatusDTO;
import com.gientech.ragcommon.index.dto.KnowledgeBaseFileDTO;
import com.gientech.ragcommon.index.request.*;
import com.gientech.ragcommon.index.utils.JSONPagination;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import com.gientech.ragindexservice.application.authz.KbAuthzService;
import com.gientech.ragindexservice.application.service.KnowledgeBaseListAppService;
import com.gientech.ragcommon.index.request.PageFileStreamReq;
import com.gientech.start.storage.exception.FileStorageException;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.InputStreamResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.io.InputStream;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

@Slf4j
@Tag(name = "知识库文件")
@RestController
@RequestMapping("/knowledgeBase/file")
public class KnowledgeBaseFileController {

    @Autowired
    private KnowledgeBaseListAppService knowledgeBaseListAppService;

    /** R13-SEC-A1：文件级授权统一折算到所属知识库，避免"按文件 id 直读/直删"绕过 */
    @Autowired
    private KbAuthzService kbAuthzService;

    @Autowired
    private com.gientech.ragindexservice.application.service.KnowledgeBaseAppService knowledgeBaseAppService;

    /** R14-C-FIX-03：引用原文预签名。凭据只在服务端参与签名，响应里只有 URL 与有效期。 */
    @Autowired
    private io.minio.MinioClient minioClient;

    @Autowired
    private com.gientech.start.storage.properties.StorageProperties storageProperties;

    private static final int PRESIGN_EXPIRES_SECONDS = 300;

    /** R13-PV-01：Office→PDF 预览服务（容器 r12-preview）。只允许经本接口访问，不再对浏览器直暴露 */
    @org.springframework.beans.factory.annotation.Value("${remote.preview-stream.url:http://127.0.0.1:18095/stream}")
    private String previewStreamUrl;

    /**
     * R13-SEC-A2：/stream 的入参是 MinIO 对象键（convertedFilePath），本身不含主体信息，
     * 是最容易被"拿到已知地址即下载"的入口。此处从对象键首段（kb_xxx）反查知识库并做对象级授权，
     * 无法归属到知识库的键一律拒绝（默认拒绝，不做"认不出就放行"）。
     */
    private void assertStreamAllowed(PageFileStreamReq req) {
        String objectKey = req == null ? null : req.getConvertedFilePath();
        if (objectKey == null || objectKey.isBlank()) {
            return;
        }
        // R14-C-FIX-23（D 报、TL 批准）：前端/第三方 `@mxmweb/fview` 会把 marker 整串塞进 query 并编码，
        // 形如 `/preview/convert?key=r12-rag%2Fkb_9%2Fdocx-plain.docx%2FV0%2Fdocx-plain.docx`。
        // 原实现按 "/" 切段找 `kb_` 前缀，整串被编码成 %2F 后切不开 → 认不出归属 → 403/30016，
        // 用户点"引用原文"打不开。这里先做一次 URL 解码 + 提取 `key=` 参数，
        // **只放宽"解析"，不放宽"授权"**：解出来的对象键仍要走后续"找 kb_ 段 → 反查 → assertRead"。
        objectKey = extractObjectKey(objectKey);
        String primitive = null;
        for (String seg : objectKey.split("/")) {
            if (seg.startsWith("kb_")) {
                primitive = seg;
                break;
            }
        }
        if (primitive == null) {
            throw new com.gientech.ragcommon.infrastructure.exception.ApplicationException(
                    com.gientech.ragcommon.global.ErrCodeEnum.INSUFFICIENT_PERMISSIONS);
        }
        com.gientech.ragcommon.index.dto.KnowledgeBaseDTO kb =
                knowledgeBaseAppService.getKbByPrimitiveName(primitive);
        if (kb == null) {
            throw new com.gientech.ragcommon.infrastructure.exception.ApplicationException(
                    com.gientech.ragcommon.global.ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        }
        kbAuthzService.assertRead(kb.getId());
    }

    private Long kbIdOfFile(Long fileId) {
        KnowledgeBaseFileDTO file = knowledgeBaseListAppService.getById(fileId);
        if (file == null) {
            throw new com.gientech.ragcommon.infrastructure.exception.ApplicationException(
                    com.gientech.ragcommon.global.ErrCodeEnum.KB_FILE_NOT_EXISTS_ERROR);
        }
        return file.getKbId();
    }

    @Operation(summary = "批量上传文件(包含文件重复性校验、父文件、多版本)")
    @PostMapping("/uploadFileList")
    @OperationLog(operateType = "上传文档")
    public Object uploadFileList(@RequestParam("uploadFileParam") String uploadFileParam, @RequestParam("files") MultipartFile[] files) {
        return knowledgeBaseListAppService.uploadFileList(uploadFileParam, files);
    }

    @Operation(summary = "批量上传文件(文档上传问答)")
    @PostMapping(value = "/uploadFiles", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @OperationLog(operateType = "上传文档")
    public Object docUploadFile(@RequestParam(value = "sessionId") String sessionId, @RequestParam("uids") List<String> uids, @RequestPart("files") MultipartFile[] files) {
        return knowledgeBaseListAppService.docUploadFile(sessionId, uids, files);
    }

    @Operation(summary = "判断文件是否上传过")
    @GetMapping("/exist")
    @OperationLog(operateType = "上传文档")
    public Boolean exist(
            @RequestParam("kbName") String kbName,
            @RequestParam("fileName") String fileName,
            @RequestParam(value = "type", defaultValue = "4", required = false) Integer type) {
        return knowledgeBaseListAppService.exist(kbName, fileName, type);
    }

    @Operation(summary = "文件预检接口")
    @GetMapping("/precheck")
    public Set<String> precheck(@RequestParam("fileNameList") List<String> fileNameList) {
        return knowledgeBaseListAppService.precheck(fileNameList);
    }

    @Operation(summary = "获取文件详情")
    @GetMapping("/getById")
    @OperationLog(operateType = "查看文档详情")
    public KnowledgeBaseFileDTO getById(@RequestParam("id") Long id) {
        KnowledgeBaseFileDTO file = knowledgeBaseListAppService.getById(id);
        if (file != null) {
            kbAuthzService.assertRead(file.getKbId());
        }
        return file;
    }

    @Operation(summary = "知识库文件列表(包含文件夹)")
    @GetMapping("/folder/list")
    @OperationLog(operateType = "查看知识库文件列表")
    public Page<KnowledgeBaseFileDTO> folderList(KnowledgeBaseFileQueryReq req) {
        return knowledgeBaseListAppService.folderList(req);
    }

    @Operation(summary = "知识库父文件以及子文件查询")
    @GetMapping("/list")
    public Page<KnowledgeBaseFileDTO> parentList(KnowledgeBaseFileQueryReq req) {
        return knowledgeBaseListAppService.listNew(req);
    }

    @Operation(summary = "文件多版本列表")
    @GetMapping("multiple/version")
    public Page<KnowledgeBaseFileDTO> multipleVersion(KnowledgeBaseFileQueryReq req) {
        return knowledgeBaseListAppService.multipleVersion(req);
    }

    @Operation(summary = "知识库文件列表")
    @GetMapping("/flatList")
    @OperationLog(operateType = "查看知识库文件列表")
    public LinkedHashSet<KnowledgeBaseFileDTO> flatList(KnowledgeBaseFileQueryReq req) {
        req.adjustIdAndIds();
        return knowledgeBaseListAppService.flatList(req);
    }

    @Operation(summary = "知识库内文件列表")
    @GetMapping("/flatFiles")
    @OperationLog(operateType = "查看知识库内文件列表")
    public Page<KnowledgeBaseFileDTO> flatFiles(KnowledgeBaseFileQueryReq req) {
        req.adjustIdAndIds();
        return knowledgeBaseListAppService.flatFiles(req);
    }

    @Operation(summary = "通过知识库id查询文件")
    @GetMapping("/queryList")
    public List<KnowledgeBaseFileDTO> queryList(@RequestParam("kbId") Long kbId, @RequestParam("types") List<Integer> types) {
        return knowledgeBaseListAppService.queryList(kbId, types);
    }

    @Operation(summary = "通过id删除文件")
    @DeleteMapping("/delete")
    @OperationLog(operateType = "删除文档")
    public Boolean delete(@Parameter(name = "id", description = "id", required = true) @RequestParam("id") Long id) {
        kbAuthzService.assertWrite(kbIdOfFile(id));
        return knowledgeBaseListAppService.deleteById(id);
    }

    @Operation(summary = "通过id批量删除文件")
    @DeleteMapping("/deleteByIds")
    @OperationLog(operateType = "批量删除文档")
    public Boolean deleteByIds(@RequestParam("fileIds") List<Long> fileIds) {
        for (Long fileId : fileIds) {
            kbAuthzService.assertWrite(kbIdOfFile(fileId));
        }
        return knowledgeBaseListAppService.deleteByIds(fileIds);
    }

    @Operation(summary = "批量查询文件")
    @GetMapping("/getByIds")
    @OperationLog(operateType = "批量查询文件")
    public List<KnowledgeBaseFileDTO> getByIds(@RequestParam("fileIds") Long[] fileIds) {
        for (Long fileId : fileIds) {
            kbAuthzService.assertRead(kbIdOfFile(fileId));
        }
        return knowledgeBaseListAppService.getByIds(fileIds);
    }

    @Operation(summary = "文件解析")
    @PostMapping("/filesParse")
    @OperationLog(operateType = "文档解析")
    public Boolean filesParse(@RequestBody FilesParseReq filesParseReq) {
        if (filesParseReq.getFileIds() != null) {
            for (String fileIdStr : filesParseReq.getFileIds()) {
                kbAuthzService.assertWrite(kbIdOfFile(Long.valueOf(fileIdStr)));
            }
        }
        return knowledgeBaseListAppService.filesParseNew(filesParseReq);
    }

    @Operation(summary = "图解析")
    @PostMapping("/graphParse")
    @OperationLog(operateType = "图解析")
    public Boolean graphParse(@RequestBody FilesParseReq filesParseReq) {
        if (filesParseReq.getFileIds() != null) {
            for (String fileIdStr : filesParseReq.getFileIds()) {
                kbAuthzService.assertWrite(kbIdOfFile(Long.valueOf(fileIdStr)));
            }
        }
        return knowledgeBaseListAppService.graphParse(filesParseReq);
    }

    @Operation(summary = "一键解析")
    @PostMapping("/filesAllParse")
    public Boolean filesAllParse(@RequestParam("kbId") Long kbId) {
        kbAuthzService.assertWrite(kbId);
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
            @RequestParam("fileMd5") String fileMd5) {
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

    @Operation(summary = "通过uid查看文件解析状态")
    @GetMapping("/getFileStatusByUids")
    public List<FileStatusDTO> getFileStatusByUid(@RequestParam("uids") List<String> uids) {
        return knowledgeBaseListAppService.getFileStatusByUids(uids);
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
            @RequestParam(value = "file", required = false) MultipartFile file,
            @RequestParam(value = "imagesFiles", required = false) List<MultipartFile> imagesFiles,
            @RequestParam(value = "tableFiles", required = false) List<MultipartFile> tableFiles,
            @RequestParam(value = "isOverwrite", defaultValue = "true", required = false) boolean isOverwrite) {
        return knowledgeBaseListAppService.uploadFile(kbId, fileId, userId, file, imagesFiles, tableFiles, isOverwrite);
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

    /**
     * R14-C-FIX-03：引用原文打开链路。
     * R13 撤销 MinIO 匿名读后，前端 `CommonEditor/utils/tools.ts` 的 `/minio/${source}` 一律 403，
     * 用户点引用打不开原文（功能性回归）。处置不是恢复匿名策略，而是由服务端签发短时效预签名 URL：
     *   1) 先做对象级授权（复用 assertStreamAllowed：认不出所属知识库即拒绝，越权 403/30016）；
     *   2) 再用服务端 MinIO 凭据签名，凭据不下发前端；
     *   3) 有效期 5 分钟。
     */
    @Operation(summary = "为对象键签发短时效预签名下载地址（引用原文打开）")
    @GetMapping("/presign")
    @OperationLog(operateType = "获取原文预签名地址")
    public java.util.Map<String, Object> presign(@RequestParam("key") String key) {
        if (key == null || key.isBlank()) {
            throw new com.gientech.ragcommon.infrastructure.exception.ApplicationException(
                    com.gientech.ragcommon.global.ErrCodeEnum.PARAM_IS_NULL);
        }
        // 对象级授权：无法归属知识库 -> KB 不存在/权限不足；越权 -> 30016
        PageFileStreamReq authReq = new PageFileStreamReq();
        authReq.setConvertedFilePath(key);
        assertStreamAllowed(authReq);

        String bucket = storageProperties.getDefaultStorageProperties().getBucketName();
        String objectKey = normalizeObjectKey(key, bucket);
        if (objectKey.isEmpty() || (bucket != null && bucket.equals(objectKey))) {
            throw new com.gientech.ragcommon.infrastructure.exception.ApplicationException(
                    com.gientech.ragcommon.global.ErrCodeEnum.INSUFFICIENT_PERMISSIONS);
        }
        // R14-C-FIX-03c：对象级授权只判"这个 kb 你能读"，不判"这个键真的存在"。
        // 实测 `r12-rag/kb_9/..../__not_exist__.docx` 也能签出 URL（HTTP 200），
        // 等于把 presign 变成"桶内任意键探测 + 签发"的接口。这里先 stat 一次，
        // 不存在就按 404 拒绝，绝不签发。
        try {
            minioClient.statObject(io.minio.StatObjectArgs.builder()
                    .bucket(bucket).object(objectKey).build());
        } catch (Exception e) {
            log.warn("presign reject: object not found key={} objectKey={} err={}", key, objectKey, e.getMessage());
            throw new com.gientech.ragcommon.infrastructure.exception.ApplicationException(
                    com.gientech.ragcommon.global.ErrCodeEnum.KB_FILE_NOT_EXISTS_ERROR);
        }
        try {
            io.minio.GetPresignedObjectUrlArgs.Builder builder = io.minio.GetPresignedObjectUrlArgs.builder()
                    .method(io.minio.http.Method.GET)
                    .bucket(bucket)
                    .object(objectKey)
                    .expiry(PRESIGN_EXPIRES_SECONDS, java.util.concurrent.TimeUnit.SECONDS);
            // R14-C-FIX-03b（D 反馈）：默认签出来的对象 content-type 是 application/octet-stream，
            // 浏览器用 <iframe> 打开会变成下载。这里按扩展名显式声明 response-content-type。
            String ct = contentTypeOfKey(objectKey);
            if (ct != null) {
                java.util.Map<String, String> extra = new java.util.HashMap<>();
                extra.put("response-content-type", ct);
                builder.extraQueryParams(extra);
            }
            String url = minioClient.getPresignedObjectUrl(builder.build());
            java.util.Map<String, Object> out = new java.util.LinkedHashMap<>();
            out.put("url", url);
            out.put("expires_in", PRESIGN_EXPIRES_SECONDS);
            out.put("objectKey", objectKey);
            return out;
        } catch (Exception e) {
            log.error("presign failed key={} objectKey={} err={}", key, objectKey, e.getMessage());
            throw new com.gientech.ragcommon.infrastructure.exception.ApplicationException(
                    com.gientech.ragcommon.global.ErrCodeEnum.READ_OBJECT_STREAM_ERROR);
        }
    }

    /**
     * 三种入参都要能吃：桶内相对对象键（ES 侧 source）、绝对 URL（MySQL converted_file_path），
     * 以及被重复拼了两次桶名的历史脏数据（r12-rag/r12-rag/kb_9/...）。
     */
    /**
     * R14-C-FIX-23：把"被整体 URL 编码进 query 的 marker"还原成对象键。
     * 只处理三种历史形态，其余原样返回：
     *   1) `/preview/convert?key=<URLEncoded 对象键>`
     *   2) `?key=<对象键>`
     *   3) 本身就是 `...%2F...` 编码串
     */
    private String extractObjectKey(String raw) {
        if (raw == null) {
            return null;
        }
        String s = raw.trim();
        try {
            int qi = s.indexOf("?");
            if (qi >= 0) {
                String query = s.substring(qi + 1);
                for (String kv : query.split("&")) {
                    if (kv.startsWith("key=")) {
                        s = kv.substring(4);
                        break;
                    }
                }
            }
            // 经过一次解码后若还含 %（双重编码），最多再解一次
            for (int i = 0; i < 2 && s.indexOf('%') >= 0; i++) {
                String decoded = java.net.URLDecoder.decode(s.replace("+", "%2B"), java.nio.charset.StandardCharsets.UTF_8);
                if (decoded.equals(s)) {
                    break;
                }
                s = decoded;
            }
        } catch (Exception e) {
            log.warn("extractObjectKey decode failed, fallback to raw. err={}", e.getMessage());
            return raw.trim();
        }
        return s;
    }

    private String normalizeObjectKey(String key, String bucket) {

        String s = key == null ? "" : key.trim();
        s = s.replaceFirst("^https?://[^/]+/", "");
        while (s.startsWith("/")) {
            s = s.substring(1);
        }
        if (bucket != null && !bucket.isBlank()) {
            while (s.startsWith(bucket + "/")) {
                s = s.substring(bucket.length() + 1);
            }
        }
        return s;
    }

    /** R14-C-FIX-03b：按对象键扩展名给出预签名响应的 content-type（只覆盖预览会用到的类型）。 */
    private String contentTypeOfKey(String objectKey) {
        if (objectKey == null) {
            return null;
        }
        String k = objectKey.toLowerCase();
        int dot = k.lastIndexOf('.');
        if (dot < 0) {
            return null;
        }
        switch (k.substring(dot + 1)) {
            case "pdf": return "application/pdf";
            case "png": return "image/png";
            case "jpg":
            case "jpeg": return "image/jpeg";
            case "gif": return "image/gif";
            case "webp": return "image/webp";
            case "bmp": return "image/bmp";
            case "svg": return "image/svg+xml";
            case "txt": return "text/plain; charset=utf-8";
            case "md": return "text/markdown; charset=utf-8";
            case "docx": return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
            case "xlsx": return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
            case "pptx": return "application/vnd.openxmlformats-officedocument.presentationml.presentation";
            default: return null;
        }
    }

    @Operation(summary = "通过知识库名和文件fileuIds查询文件，fileUids如果是null，查询当前知识库下所有的文件")
    @GetMapping("/getByKbNameAndUid")
    public List<KnowledgeBaseFileDTO> getByKbNameAndUid(@RequestParam("kbName") String kbName, @RequestParam(value = "fileUids", required = false) List<String> fileUids) {
        return knowledgeBaseListAppService.getByKbNameAndUid(kbName, fileUids);
    }

    @Operation(summary = "通过uid删除")
    @DeleteMapping("/deleteByUid")
    public List<KnowledgeBaseFileDTO> deleteByUid(@RequestParam(value = "queryId") String queryId, @RequestParam(value = "uid") String fileUid) {
        return knowledgeBaseListAppService.deleteByUid(queryId, fileUid);
    }

    @Operation(summary = "文件归集-创建集合")
    @PostMapping("/createCollect")
    public Boolean createCollect(@RequestBody @Validated CreateCollectReq createCollectReq) {
        return knowledgeBaseListAppService.createCollect(createCollectReq);
    }

    @Operation(summary = "文件归集-将文件移除文件集")
    @PostMapping("/remove")
    public Boolean remove(@RequestBody @Validated RemoveCollectReq removeCollectReq) {
        return knowledgeBaseListAppService.remove(removeCollectReq);
    }

    @Operation(summary = "文件归集-文件/文件集转移")
    @PostMapping("/transfer")
    public Boolean transfer(@RequestBody @Validated FileCollectTransferReq fileCollectTransferReq) {
        return knowledgeBaseListAppService.transfer(fileCollectTransferReq);
    }

    @Operation(summary = "文件归集-解散")
    @PostMapping("/dissolve")
    public Boolean dissolve(@RequestBody @Validated DissolveCollectReq dissolveCollectReq) {
        return knowledgeBaseListAppService.dissolve(dissolveCollectReq);
    }

    @Operation(summary = "文件归集-查询文件集")
    @GetMapping("/collect/list")
    public List<CollectDTO> collectList(@RequestParam("kbId") Long kbId, @RequestParam("fileListType") Integer fileListType) {
        return knowledgeBaseListAppService.collectList(kbId, fileListType);
    }

    @Operation(summary = "文件归集-通过文件集id查询")
    @GetMapping("/getByGroupId")
    public List<KnowledgeBaseFileDTO> getByGroupId(@RequestParam("kbId") Long kbId, @RequestParam("groupId") String groupId, @RequestParam("fileListType") Integer fileListType) {
        return knowledgeBaseListAppService.getByGroupId(kbId, groupId, fileListType);
    }

    @Operation(summary = "文件归集-散落的文件")
    @GetMapping("/scatter/list")
    public List<KnowledgeBaseFileDTO> scatterList(
            @RequestParam("kbId") Long kbId,
            @RequestParam(value = "fileListType", required = false, defaultValue = "1") Integer fileListType) {
        return knowledgeBaseListAppService.scatterList(kbId, fileListType);
    }

    @Operation(summary = "给文件添加标签")
    @PostMapping("/addLabel")
    public Boolean addLabel(@RequestParam("fileId") Long fileId, @RequestParam("label") String label) {
        return knowledgeBaseListAppService.addLabel(fileId, label);
    }

    @Operation(summary = "Office 预览（先对象级鉴权，再转 PDF 流）")
    @PostMapping("/previewStream")
    public ResponseEntity<byte[]> previewStream(@RequestBody @Valid PageFileStreamReq req) {
        // 与 /stream 同一套授权口径：从对象键反查知识库，认不出归属的一律拒绝；
        // 预览服务在 127.0.0.1:18095 内部端口不做鉴权，这里是唯一收口点。
        assertStreamAllowed(req);
        org.springframework.http.client.SimpleClientHttpRequestFactory f =
                new org.springframework.http.client.SimpleClientHttpRequestFactory();
        f.setConnectTimeout(15000);
        f.setReadTimeout(90000);
        org.springframework.web.client.RestTemplate rt = new org.springframework.web.client.RestTemplate(f);
        org.springframework.http.HttpHeaders in = new org.springframework.http.HttpHeaders();
        in.setContentType(MediaType.APPLICATION_JSON);
        java.util.Map<String, Object> body = new java.util.HashMap<>();
        body.put("convertedFilePath", req.getConvertedFilePath());
        ResponseEntity<byte[]> resp;
        try {
            resp = rt.postForEntity(previewStreamUrl,
                    new org.springframework.http.HttpEntity<>(body, in), byte[].class);
        } catch (Exception ex) {
            log.error("preview convert failed for key {}", req.getConvertedFilePath(), ex);
            throw new com.gientech.ragcommon.infrastructure.exception.ApplicationException(
                    com.gientech.ragcommon.global.ErrCodeEnum.CONVERT_FILE_ERROR);
        }
        org.springframework.http.HttpHeaders out = new org.springframework.http.HttpHeaders();
        out.setContentType(MediaType.APPLICATION_PDF);
        out.set(HttpHeaders.CONTENT_DISPOSITION, "inline; filename=\"preview.pdf\"");
        out.setCacheControl("no-store");
        return new ResponseEntity<>(resp.getBody(), out,
                resp.getStatusCode().is2xxSuccessful() ? org.springframework.http.HttpStatus.OK
                        : org.springframework.http.HttpStatus.BAD_GATEWAY);
    }

    @Operation(summary = "返回文件流")
    @PostMapping("/stream")
    public ResponseEntity<?> pageFileStream(@RequestBody @Valid PageFileStreamReq pageFileStreamReq) throws IOException, FileStorageException {
        assertStreamAllowed(pageFileStreamReq);
        HttpHeaders headers = new HttpHeaders();
        if (pageFileStreamReq.isStream()) {
            headers.setContentType(MediaType.APPLICATION_OCTET_STREAM);
            InputStream inputStream = knowledgeBaseListAppService.pageFileStream(pageFileStreamReq, headers);
            InputStreamResource inputStreamResource = new InputStreamResource(inputStream);
            return ResponseEntity.ok().headers(headers).body(inputStreamResource);
        } else {
            headers.setContentType(MediaType.APPLICATION_JSON);
            JSONPagination.PageResult<JsonNode> jsonNodePageResult = knowledgeBaseListAppService.pageFile(pageFileStreamReq, headers);
            return ResponseEntity.ok().headers(headers).body(jsonNodePageResult);
        }
    }

    @Operation(summary = "获取文件总页数/块数")
    @GetMapping("/totalPages")
    public Integer totalPages(@RequestParam("fileId") Long fileId) {
        return knowledgeBaseListAppService.totalPages(fileId);
    }

    @Operation(summary = "查询文档解析当前排队信息")
    @GetMapping("/getSequenceCodeByFileId")
    @OperationLog(operateType = "查询文档解析当前排队信息")
    public Long getSequenceCodeByFileId(@RequestParam("fileId") Long fileId) {
        return knowledgeBaseListAppService.getSequenceCodeByFileId(fileId);
    }
}
