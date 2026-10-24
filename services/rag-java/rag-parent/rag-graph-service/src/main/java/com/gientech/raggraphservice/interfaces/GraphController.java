package com.gientech.raggraphservice.interfaces;

import com.gientech.ragcommon.graph.dto.*;
import com.gientech.ragcommon.graph.enums.GraphFieldEnums;
import com.gientech.raggraphservice.application.service.GraphQueryAppService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import java.util.List;

@RestController
@RequestMapping("/info")
@Tag(name = "图基本信息询接口")
@Slf4j
public class GraphController {

    @Autowired
    private GraphQueryAppService graphQueryAppService;

    @GetMapping("/nodes")
    @Operation(summary = "查询点以及点的属性")
    public List<NodeDTO> nodes(@RequestParam("spaceName") String spaceName,@RequestParam(value = "fileId",required = false) Long fileId)  {
        return graphQueryAppService.nodes(GraphFieldEnums.GRAPH_SPACENAME_PREFIX +spaceName,fileId);
    }

    @GetMapping("/edges")
    @Operation(summary = "查询边以及边的属性")
    public List<EdgeDTO> edges(@RequestParam("spaceName") String spaceName,@RequestParam(value = "fileId",required = false) Long fileId)  {
        return graphQueryAppService.edges(GraphFieldEnums.GRAPH_SPACENAME_PREFIX + spaceName,fileId);
    }

}