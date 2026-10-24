package com.gientech.raggraphservice.interfaces;

import com.gientech.ragcommon.graph.dto.*;
import com.gientech.ragcommon.graph.enums.GraphFieldEnums;
import com.gientech.ragcommon.graph.request.*;
import com.gientech.raggraphservice.application.service.GraphQueryAppService;
import com.gientech.raggraphservice.application.service.GraphSearchAppService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import java.util.List;
import java.util.Map;

/**
 * 图谱实例查询Controller接口
 *
 * @author liutaiyun
 * @since 2023/02/14 15:34
 **/
@RestController
@RequestMapping("/search")
@Tag(name = "图查询接口")
@Slf4j
public class GraphSearchController {

    @Autowired
    private GraphQueryAppService graphQueryAppService;

    @Autowired
    private GraphSearchAppService graphSearchAppService;


    @GetMapping("/instances")
    @Operation(summary = "节点和边的实例数查询")
    public Map<Long,GraphInstanceDTO> instance(@RequestParam("spaceName") String spaceName, @RequestParam("fileIds") List<Long> fileIds)  {
        return graphQueryAppService.instance(GraphFieldEnums.GRAPH_SPACENAME_PREFIX + spaceName,fileIds);
    }

    @PostMapping("/nodeSearch")
    @Operation(summary = "节点查询")
    public GraphDataDTO searchNodes(@RequestBody @Validated NodeSearchRequest nodeSearchRequest){
        GraphDataDTO graphDataDTO = graphQueryAppService.queryNodesByCondition(nodeSearchRequest);
        return graphDataDTO;
    }

    @PostMapping("/edgeSearch")
    @Operation(summary = "关系查询")
    public GraphDataDTO searchEdges(@RequestBody @Validated EdgeSearchRequest edgeSearchRequest) {
        GraphDataDTO graphDataDTO = graphQueryAppService.queryEdgesByCondition(edgeSearchRequest);
        return graphDataDTO;
    }

    @GetMapping("/keywordSearch")
    @Operation(summary = "节点关键字提示查询")
    public List<KeywordDTO> keywordSearch(KeywordSearchRequest keywordSearch){
        return graphQueryAppService.keywordSearch(keywordSearch);
    }

    @PostMapping("/pathSearch")
    @Operation(summary = "路径查询")
    public List<PathDTO> searchPath(@RequestBody @Validated PathSearchRequest pathSearchRequest) throws Exception {
        List<PathDTO> paths = graphSearchAppService.pathSearch(pathSearchRequest);
        return paths;
    }

    @PostMapping("/cypherSearch")
    @Operation(summary = "cypher语句查询")
    public List<GraphDataDTO.CypherResultTableRow> cypherSearch(@RequestBody CypherSearchRequest cypherSearchRequest) {
        List<GraphDataDTO.CypherResultTableRow> rows = graphQueryAppService.queryByCypherWithTableData(cypherSearchRequest.getSpaceName(), cypherSearchRequest.getCypher(),cypherSearchRequest.getFileId());
        return rows;
    }

    @PostMapping("/searchNodesByIds")
    @Operation(summary = "根据vid批量查询节点")
    public List<NodeDataDTO> searchNodesByIds(@RequestBody NodeBatchSearchRequest nodeBatchSearchRequest) {
        return graphQueryAppService.queryNodesByIds(nodeBatchSearchRequest);
    }

    @PostMapping("/nodeStepSearch")
    @Operation(summary = "展开节点")
    public GraphDataDTO searchNodeOneStep(@RequestBody @Validated NodeStepSearchRequest nodeStepSearchRequest) {
        GraphDataDTO graphDataDTO = graphSearchAppService.searchNodeOneStep(nodeStepSearchRequest);
        return graphDataDTO;
    }

    @PostMapping("/wholeGraphSearch")
    @Operation(summary = "全图查询")
    public GraphDataDTO wholeGraphSearch(@RequestBody @Validated WholeGraphSearchRequest wholeGraphSearchRequest){
        GraphDataDTO graphDataDTO = graphSearchAppService.wholeGraphSearch(wholeGraphSearchRequest);
        return graphDataDTO;
    }

    @GetMapping("/canSearchNodeOneStep")
    @Operation(summary = "能否展开节点1度关系")
    public Boolean canSearchNodeOneStep(@RequestParam("spaceName") String spaceName,
                                        @RequestParam("nodeType") String nodeType,
                                        @RequestParam("nodeInstanceId") String nodeInstanceId){
        return graphSearchAppService.canSearchNodeOneStep(GraphFieldEnums.GRAPH_SPACENAME_PREFIX + spaceName, nodeType, nodeInstanceId);
    }

    @PostMapping("/commonNeighbourSearch")
    @Operation(summary = "共同邻居查询")
    public List<NeighbourNodeDTO> commonNeighbourSearch(@RequestBody CommonNeighbourRequest commonNeighbourRequest){
        List<NeighbourNodeDTO> neighbourNodeDTOS = graphSearchAppService.commonNeighbourSearch(commonNeighbourRequest);
        return neighbourNodeDTOS;
    }

    @GetMapping("/subGraph")
    @Operation(summary = "获取子图--用户进入图谱后看到的子图")
    public GraphDataDTO subGraph(@RequestParam("spaceName") String spaceName) {
        return graphSearchAppService.subGraph(GraphFieldEnums.GRAPH_SPACENAME_PREFIX + spaceName);
    }

    @GetMapping("/ping")
    @Operation(summary = "仅前端测试Graph是否可用")
    public Boolean ping()  {
        return true;
    }

    @GetMapping("/file/pageNum")
    @Operation(summary = "通过文件id和pdf的页码查询")
    public GraphDataDTO searchByFile(@RequestParam("spaceName") String spaceName,@RequestParam("fileId") Long fileId,@RequestParam("pageNum") Integer pageNum) {
        GraphDataDTO graphDataDTO = graphQueryAppService.searchByFile(GraphFieldEnums.GRAPH_SPACENAME_PREFIX + spaceName,fileId,pageNum);
        return graphDataDTO;
    }
}