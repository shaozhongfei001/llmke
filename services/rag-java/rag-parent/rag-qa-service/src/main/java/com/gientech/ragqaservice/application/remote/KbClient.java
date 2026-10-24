package com.gientech.ragqaservice.application.remote;

import cn.hutool.db.Entity;
import com.fasterxml.jackson.databind.JsonNode;
import com.gientech.ragcommon.feign.FeignCustomConfig;
import com.gientech.ragcommon.index.dto.FileChunkDTO;
import com.gientech.ragcommon.index.dto.FileStatusDTO;
import com.gientech.ragcommon.index.dto.KnowledgeBaseDTO;
import com.gientech.ragcommon.index.dto.KnowledgeBaseFileDTO;
import com.gientech.ragcommon.index.dto.tools.TLDatabaseDTO;
import com.gientech.ragcommon.index.dto.tools.TLTableDataDto;
import com.gientech.ragcommon.index.dto.tools.TLTableDto;
import com.gientech.ragcommon.index.request.PageFileStreamReq;
import com.gientech.ragcommon.index.request.QueryDataReq;
import com.gientech.ragcommon.index.utils.JSONPagination;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import com.gientech.start.storage.exception.FileStorageException;
import jakarta.validation.Valid;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;
import java.util.Set;

@FeignClient(name = "rag-index-service", path = "index", configuration = FeignCustomConfig.class)
public interface KbClient {

    /**
     * 通过知识库id查询文件
     *
     * @param kbId
     * @param types
     * @return
     */
    @GetMapping("/knowledgeBase/file/queryList")
    List<KnowledgeBaseFileDTO> queryList(@RequestParam("kbId") Long kbId, @RequestParam("types") List<Integer> types);

    /**
     * 删除知识库
     *
     * @param id
     * @return
     */
    @DeleteMapping("/knowledgeBase/delete")
    Boolean deleteById(@RequestParam("id") Long id);

    /**
     * 通过知识库名查询知识库信息
     *
     * @param primitiveName
     * @return
     */
    @GetMapping("/knowledgeBase/getKbByPrimitiveName")
    KnowledgeBaseDTO getKbByPrimitiveName(@RequestParam("primitiveName") String primitiveName);

    /**
     * 通过id查询知识库信息
     *
     * @param id
     * @return
     */
    @GetMapping("/knowledgeBase/getKbById")
    KnowledgeBaseDTO getKbById(@RequestParam(value = "id") Long id);

    /**
     * 通过知识库名和文件fileuIds查询文件，fileUids如果是null，查询当前知识库下所有的文件
     *
     * @param kbName
     * @param fileUids
     * @return
     */
    @GetMapping("/knowledgeBase/file/getByKbNameAndUid")
    List<KnowledgeBaseFileDTO> getByKbNameAndUid(@RequestParam("kbName") String kbName, @RequestParam(value = "fileUids", required = false) List<String> fileUids);

    /**
     * 通过知识库名和文件名查询文本块
     *
     * @param kbName
     * @param fileName
     * @param pageNo
     * @param pageSize
     * @return
     */
    @GetMapping("/knowledgeBase/file/getKbFileChunks")
    List<FileChunkDTO> getKbFileChunks(@RequestParam("kbName") String kbName, @RequestParam("fileName") String fileName, @RequestParam("pageNo") Integer pageNo, @RequestParam("pageSize") Integer pageSize);

    @GetMapping("/knowledgeBase/file/getByIds")
    List<KnowledgeBaseFileDTO> getByIds(@RequestParam("fileIds") List<Long> ids);

    @GetMapping("/knowledgeBase/searchList")
    Set<KnowledgeBaseDTO> searchList();

    /**
     * 批量上传文件(文档上传问答)
     *
     * @param sessionId
     * @param uids
     * @param files
     * @return
     */
    @PostMapping(value = "/knowledgeBase/file/uploadFiles", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    @OperationLog(operateType = "批量上传文件(文档上传问答)")
    Object docUploadFile(@RequestParam(value = "sessionId") String sessionId, @RequestParam("uids") List<String> uids, @RequestPart("files") MultipartFile[] files);


    /**
     * 判断文件是否上传过
     *
     * @param kbName
     * @param fileName
     * @param type
     * @return
     */
    @GetMapping("/knowledgeBase/file/exist")
    @OperationLog(operateType = "判断文件是否上传过")
    Boolean exist(
            @RequestParam("kbName") String kbName,
            @RequestParam("fileName") String fileName,
            @RequestParam(value = "type", defaultValue = "4", required = false) Integer type);


    /**
     * 通过uid查看文件解析状态
     *
     * @param uids
     * @return
     */
    @GetMapping("/knowledgeBase/file/getFileStatusByUids")
    List<FileStatusDTO> getFileStatusByUid(@RequestParam("uids") List<String> uids);

    /**
     * 通过uid删除
     *
     * @param queryId
     * @param fileUid
     * @return
     */
    @DeleteMapping("/knowledgeBase/file/deleteByUid")
    List<KnowledgeBaseFileDTO> deleteByUid(@RequestParam(value = "queryId") String queryId, @RequestParam(value = "uid") String fileUid);


    /**
     * 根据sql查询数据
     *
     * @param executeSqlReq
     * @return
     */
    @PostMapping("/database/queryData")
    List<Entity> queryData(@RequestBody QueryDataReq executeSqlReq);

    @PostMapping("/knowledgeBase/file/stream")
    ResponseEntity<JSONPagination.PageResult<JsonNode>> pageFileStream(@RequestBody @Valid PageFileStreamReq pageFileStreamReq) throws IOException, FileStorageException;


    @GetMapping("/database/{databaseId}")
    TLDatabaseDTO queryDB(@PathVariable("databaseId") Long databaseId);

    @GetMapping("/database/dataTable/queryTableMeta/{tableId}")
    TLTableDto queryDataTableTableMeta(@PathVariable("tableId") Long tableId);

    @GetMapping("/database/dataTable/queryTableFileData/{databaseId}/{tableId}")
    TLTableDataDto queryTableFileDataByTableId(
            @PathVariable("databaseId") Long databaseId,
            @PathVariable("tableId") Long tableId,
            @RequestParam(value = "pageNo", required = false) Long pageNo,
            @RequestParam(value = "pageSize", required = false) Long pageSize);


    @GetMapping("/database/directDB/queryTableMeta/{databaseId}/{tableName}")
    TLTableDto queryDirectDBTableMeta(@PathVariable("databaseId") Long databaseId,
                                  @PathVariable("tableName") String tableName);

    @GetMapping("/database/directDB/queryTableData/{databaseId}/{tableName}")
    TLTableDataDto queryTableData(@PathVariable("databaseId") Long databaseId,
                                  @PathVariable("tableName") String tableName,
                                  @RequestParam(value = "pageNo", required = false, defaultValue = "1") Long pageNo,
                                  @RequestParam(value = "pageSize", required = false, defaultValue = "100") Long pageSize);
}