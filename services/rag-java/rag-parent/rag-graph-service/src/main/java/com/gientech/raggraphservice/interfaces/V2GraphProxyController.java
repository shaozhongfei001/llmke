package com.gientech.raggraphservice.interfaces;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * D0：库级图谱查看数据源切换到 HippoRAG 图服务（18094 /v2/graph/view）。
 *
 * 前端 GraphCanvas 的旧入口是 Nebula（wholeGraphSearch / subGraph）。本控制器把旧契约
 * （{nodeList, edgeList}，node={vid,name,nodeType,properties}，edge={id,edgeType,src,dst}）
 * 平移到 V2 视图数据源，调用方（GraphCanvas）只需换 URL，不改解析逻辑。
 *
 * V2 图服务不可用时如实返回 200 + 空列表 + notice（前端可渲染空态），不冒充 Nebula 数据。
 */
@RestController
@RequestMapping("/search")
@Tag(name = "V2 库级图查看（HippoRAG）")
@Slf4j
public class V2GraphProxyController {

    @Value("${llmke.v2.graph-api:http://127.0.0.1:18094}")
    private String v2GraphApi;

    @PostMapping("/v2WholeGraph")
    @Operation(summary = "库级图：转发 18094 /v2/graph/view，输出前端 GraphCanvas 契约")
    public Map<String, Object> v2WholeGraph(@RequestBody(required = false) Map<String, Object> req) {
        Map<String, Object> out = new LinkedHashMap<>();
        List<Map<String, Object>> nodeList = new ArrayList<>();
        List<Map<String, Object>> edgeList = new ArrayList<>();
        out.put("nodeList", nodeList);
        out.put("edgeList", edgeList);
        try {
            // 按库路由：把 spaceName（知识库标识，如 kb_9）透传给 18094 的 kb 参数。
            // 18094 按 kb 找对应快照，找不到返回 NOT_BUILT —— 绝不用别的库的快照冒充。
            String spaceName = req == null ? "" : String.valueOf(req.getOrDefault("spaceName", ""));
            if (spaceName.isBlank()) {
                out.put("notice", "缺少 spaceName（知识库标识），无法定位该库图谱");
                return out;
            }
            String encoded = URLEncoder.encode(spaceName, StandardCharsets.UTF_8);
            String url = v2GraphApi.replaceAll("/+$", "") + "/v2/graph/view?kb=" + encoded;
            @SuppressWarnings("unchecked")
            Map<String, Object> view = new RestTemplate().getForObject(url, Map.class);
            if (view == null) {
                out.put("notice", "V2 图服务无响应");
                return out;
            }
            if (!"ok".equals(String.valueOf(view.get("status")))) {
                // NOT_BUILT / GRAPH_UNAVAILABLE：如实透出原因，不返回别的库数据
                out.put("notice", String.valueOf(view.getOrDefault("reason",
                        "V2 图服务未就绪: " + view.get("status"))));
                return out;
            }
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> nodes = (List<Map<String, Object>>) view.getOrDefault("nodes", List.of());
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> edges = (List<Map<String, Object>>) view.getOrDefault("edges", List.of());
            // 节点 id → name 索引，供边补端点可读名
            Map<String, String> nameById = new HashMap<>();
            int eid = 0;
            for (Map<String, Object> n : nodes) {
                Map<String, Object> node = new HashMap<>();
                String vid = String.valueOf(n.getOrDefault("id", ""));
                String name = String.valueOf(n.getOrDefault("name", vid));
                String kind = String.valueOf(n.getOrDefault("kind", "entity"));
                String type = String.valueOf(n.getOrDefault("type", "实体"));
                node.put("vid", vid);
                node.put("name", name);
                node.put("nodeType", type);
                Map<String, Object> props = new HashMap<>();
                props.put("kind", kind);
                props.put("title", name);
                node.put("properties", props);
                nodeList.add(node);
                nameById.put(vid, name);
            }
            for (Map<String, Object> e : edges) {
                Map<String, Object> edge = new HashMap<>();
                String srcVid = String.valueOf(e.getOrDefault("source", ""));
                String dstVid = String.valueOf(e.getOrDefault("target", ""));
                edge.put("id", String.valueOf(e.getOrDefault("id", "v2-e" + (eid++))));
                edge.put("edgeType", e.getOrDefault("predicate", "关联"));
                Map<String, Object> src = new HashMap<>();
                src.put("vid", srcVid);
                src.put("name", nameById.getOrDefault(srcVid, srcVid));
                Map<String, Object> dst = new HashMap<>();
                dst.put("vid", dstVid);
                dst.put("name", nameById.getOrDefault(dstVid, dstVid));
                edge.put("src", src);
                edge.put("dst", dst);
                edgeList.add(edge);
            }
            return out;
        } catch (Exception ex) {
            log.warn("v2WholeGraph proxy failed: {}", ex.getMessage());
            out.put("notice", "V2 图服务不可用: " + ex.getMessage());
            return out;
        }
    }
}
