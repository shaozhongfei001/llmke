package com.gientech.ragindexservice.interfaces;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.OpenApiHeader;
import com.gientech.ragcommon.index.dto.KbEmbeddingModelDTO;
import com.gientech.ragcommon.index.dto.KbParseTypeDTO;
import com.gientech.ragcommon.index.dto.KnowledgeBaseDTO;
import com.gientech.ragcommon.index.request.KbConfUpdateReq;
import com.gientech.ragcommon.index.request.KnowledgeBaseCreateReq;
import com.gientech.ragcommon.index.request.KnowledgeBaseQueryReq;
import com.gientech.ragcommon.index.request.KnowledgeBaseUpdateReq;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import com.gientech.ragindexservice.application.service.KnowledgeBaseAppService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletRequest;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Set;

/**
 * <p>
 * 知识库 前端控制器
 * </p>
 *
 * @author wudf
 * @since 2024-06-04
 */
@Tag(name = "知识库接口")
@RestController
@RequestMapping("/knowledgeBase")
public class KnowledgeBaseController {

    @Autowired
    private KnowledgeBaseAppService knowledgeBaseAppService;

    @Operation(summary = "创建知识库")
    @PostMapping("/create")
    @OperationLog(operateType = "创建知识库")
    public KnowledgeBaseDTO createKb(HttpServletRequest request, @Validated @RequestBody KnowledgeBaseCreateReq kbReq) {
        kbReq.setPlatform(OpenApiHeader.getPlatformHeader(request));
        return knowledgeBaseAppService.createKb(kbReq);
    }

    @Operation(summary = "删除知识库")
    @DeleteMapping("/delete")
    @OperationLog(operateType = "删除知识库")
    public Boolean deleteById(@Parameter(name = "id", description = "知识库id", required = true) @RequestParam("id") Long id) {
        return knowledgeBaseAppService.deleteById(id);
    }

    @Operation(summary = "知识库列表数据")
    @GetMapping("/list")
    @OperationLog(operateType = "查询知识库列表")
    public Page<KnowledgeBaseDTO> list(HttpServletRequest request, KnowledgeBaseQueryReq knowledgeBaseQueryReq) {
        knowledgeBaseQueryReq.setPlatform(OpenApiHeader.getPlatformHeader(request));
        return knowledgeBaseAppService.list(knowledgeBaseQueryReq);
    }

    @Operation(summary = "共享知识库列表数据")
    @GetMapping("/share/list")
    @OperationLog(operateType = "查询共享知识库列表")
    public Page<KnowledgeBaseDTO> shareList(HttpServletRequest request, KnowledgeBaseQueryReq knowledgeBaseQueryReq) {
        knowledgeBaseQueryReq.setPlatform(OpenApiHeader.getPlatformHeader(request));
        return knowledgeBaseAppService.shareList(knowledgeBaseQueryReq);
    }

    @Operation(summary = "所有知识库数据(用户自己的知识库 + 共享数据的知识库)")
    @GetMapping("/searchList")
    public Set<KnowledgeBaseDTO> searchList(HttpServletRequest request, @RequestParam(value = "fuzzy", required = false) String fuzzy, @RequestParam(value = "userName", required = false) String userName) {
        String platform = OpenApiHeader.getPlatformHeader(request);
        if(StringUtils.isEmpty(userName))
            userName = UserContext.getUser().getUserName();
        return knowledgeBaseAppService.searchList(fuzzy, userName, platform);
    }

    @Operation(summary = "更新")
    @PutMapping("/update")
    @OperationLog(operateType = "编辑知识库")
    public Boolean update(@RequestBody KnowledgeBaseUpdateReq knowledgeBaseUpdateReq) {
        return knowledgeBaseAppService.update(knowledgeBaseUpdateReq);
    }

    @Operation(summary = "通过id查询知识库信息")
    @GetMapping("/getKbById")
    public KnowledgeBaseDTO getKbById(@Parameter(name = "id", description = "知识库id", required = true) @RequestParam(value = "id") Long id) {
        return knowledgeBaseAppService.getKbById(id);
    }

    @Operation(summary = "通过知识库名查询知识库信息")
    @GetMapping("/getKbByPrimitiveName")
    public KnowledgeBaseDTO getKbByPrimitiveName(@RequestParam("primitiveName") String primitiveName) {
        return knowledgeBaseAppService.getKbByPrimitiveName(primitiveName);
    }

    @Operation(summary = "更新知识库解析配置")
    @PutMapping("/updateConf")
    @OperationLog(operateType = "编辑知识库配置")
    public Boolean updateConf(@RequestBody KbConfUpdateReq updateConf) {
        return knowledgeBaseAppService.updateConf(updateConf);
    }

    @Operation(summary = "知识库解析配置是否可编辑")
    @GetMapping("/canUpdateConf")
    public Boolean canUpdateConf(@RequestParam(value = "id") Long id) {
        return knowledgeBaseAppService.canUpdateConf(id);
    }

    @Operation(summary = "根据旧知识库重建新知识库并解析所有原知识库文档")
    @PostMapping("/rebuildNew")
    public KnowledgeBaseDTO rebuildNew(@RequestParam(value = "id") Long id) {
        return knowledgeBaseAppService.rebuildNew(id);
    }

    @Operation(summary = "重新解析所有知识库文档")
    @PostMapping("/reParse")
    public Boolean reParse(@RequestParam(value = "id") Long id) {
        return knowledgeBaseAppService.reParse(id);
    }

    @Operation(summary = "下载知识库所有文档")
    @PostMapping("/downloadKbFiles")
    @OperationLog(operateType = "下载知识库文档")
    public Boolean downloadKbFiles(@RequestParam(value = "id", required = true) Long id) {
        return knowledgeBaseAppService.downloadKbFiles(id);
    }

    @Operation(summary = "转移知识库")
    @GetMapping("/transferProperty")
    public Boolean transferKbProperty(@RequestParam("owner") String owner, @RequestParam("receiver") String receiver) {
        return knowledgeBaseAppService.transferProperty(owner, receiver);
    }
}
