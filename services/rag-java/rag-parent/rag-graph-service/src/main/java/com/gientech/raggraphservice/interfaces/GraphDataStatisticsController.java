package com.gientech.raggraphservice.interfaces;

import com.gientech.ragcommon.graph.enums.GraphFieldEnums;
import com.gientech.raggraphservice.application.service.GraphDataStatisticsAppService;
import com.gientech.ragcommon.graph.dto.GraphDataStatisticsDTO;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

/**
 * 图数据统计接口类
 *
 * @author chenjuan
 * @since 2023/3/2 18:58
 */

@Slf4j
@RestController
@RequestMapping("/graphStatistics")
@Tag(name = "图谱统计信息接口")
public class GraphDataStatisticsController {

    @Autowired
    private GraphDataStatisticsAppService graphDataStatisticsAppService;

    @GetMapping("/getWholeGraphStatistics")
    @Operation(summary = "图统计查询")
    public GraphDataStatisticsDTO getWholeGraphStatistics(@RequestParam("spaceName") String spaceName,@RequestParam(value = "fileId",required = false) Long fileId){
        return graphDataStatisticsAppService.getWholeDataStatistics(GraphFieldEnums.GRAPH_SPACENAME_PREFIX+spaceName,fileId);
    }

}
