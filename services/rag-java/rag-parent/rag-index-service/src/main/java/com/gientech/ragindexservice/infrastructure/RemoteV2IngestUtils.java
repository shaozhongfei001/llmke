package com.gientech.ragindexservice.infrastructure;

import com.alibaba.fastjson2.JSONObject;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

/**
 * V2 摄取触发：解析完成后，把同一份解析快照交给搜索与图谱两路消费。
 *
 * 为什么调用点放在 rag-index-service：它是"解析完成"的唯一知情者（taskCallback/doSuccess）。
 * 真正的封快照 / 投影 / 按库建图在 Python 侧（kb_ingest_service:18096），本类只负责触发与
 * **如实回传结果**，不做业务判断。
 *
 * 未配置 url 时返回 null（保持旧行为），绝不假装触发成功。
 */
@Slf4j
@Component
public class RemoteV2IngestUtils {

    private final RestTemplate restTemplate = new RestTemplate();

    /** 未配置即关闭：默认空串，避免默认打开改变线上行为。 */
    @Value("${remote.v2-ingest.url:}")
    private String remoteV2IngestUrl;

    public boolean enabled() {
        return remoteV2IngestUrl != null && !remoteV2IngestUrl.trim().isEmpty();
    }

    /**
     * 触发一次知识库摄取。
     *
     * 两种输入模式（二选一）：
     * - `doc2mdDir`：解析链路已产出 doc2md 四件套，只需双路消费；
     * - `fileUrl`  ：给平台文件地址，由摄取服务下载原件并跑 doc2md（全自动）。
     *
     * @param kb        知识库标识（primitiveName，如 kb_9），不可为空
     * @param fileId    平台文件 id
     * @param doc2mdDir doc2md 解析产物目录（可为空）
     * @param fileUrl   平台文件地址（MinIO URL，可为空）
     * @param fileName  原始文件名（用于溯源显示）
     * @param filePath  文件路径（用于溯源定位）
     * @param fileSize  文件大小
     * @return 上游响应体；未配置或参数不全时返回 null
     */
    public String ingest(String kb, Long fileId, String doc2mdDir, String fileUrl,
                         String fileName, String filePath, Long fileSize) {
        if (!enabled()) {
            return null;
        }
        boolean hasDir = doc2mdDir != null && !doc2mdDir.trim().isEmpty();
        boolean hasUrl = fileUrl != null && !fileUrl.trim().isEmpty();
        if (kb == null || kb.trim().isEmpty() || fileId == null || (!hasDir && !hasUrl)) {
            // 既没产物目录也没文件地址时没有输入可交；
            // 不能拿 legacy 正文顶上：那不是同一份解析，引用会和召回内容对不上。
            log.warn("V2 摄取跳过：kb/fileId/doc2mdDir/fileUrl 不完整 kb={} fileId={} dir={} url={}",
                    kb, fileId, doc2mdDir, fileUrl);
            return null;
        }

        JSONObject payload = new JSONObject();
        payload.put("kb", kb);
        payload.put("file_id", fileId);
        if (hasDir) {
            payload.put("doc2md_dir", doc2mdDir);
        }
        if (hasUrl) {
            payload.put("file_url", fileUrl);
        }
        if (fileName != null) {
            payload.put("file_name", fileName);
        }
        if (filePath != null) {
            payload.put("file_path", filePath);
        }
        if (fileSize != null) {
            payload.put("file_size", fileSize);
        }

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<String> entity = new HttpEntity<>(payload.toJSONString(), headers);
        log.info("V2 摄取请求 url={} params={}", remoteV2IngestUrl, payload.toJSONString());
        ResponseEntity<String> response =
                restTemplate.exchange(remoteV2IngestUrl, HttpMethod.POST, entity, String.class);
        String body = response.getBody();
        if (body != null) {
            JSONObject json = JSONObject.parseObject(body);
            Integer code = json == null ? null : json.getInteger("code");
            if (code == null || (code != 200 && code != 207)) {
                // 207 = 搜索路成功、图谱路失败：必须让调用方看见，不吞
                log.error("V2 摄取未完全成功 code={} body={}", code, body);
            }
        }
        return body;
    }
}
