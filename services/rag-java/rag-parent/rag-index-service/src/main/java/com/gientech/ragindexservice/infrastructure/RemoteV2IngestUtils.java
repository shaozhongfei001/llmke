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
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.RestClientException;
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
    /**
     * 摄取结果。**故意不用 boolean**：调用方需要区分「可重试」与「不可重试」。
     *
     * 判定依据（P4-L13-B 必核项实测结论，两侧都要看）：
     * 1) **HTTP 状态码**：`RestTemplate.exchange` 对 4xx/5xx 会抛异常，
     *    所以「非 2xx」走 catch 分支 —— 这正是 L12 修 `response.status_code = code` 的必要性：
     *    若 Python 侧恒返 200（只在 body 里写 code=409），RestTemplate 不会抛，
     *    调用方就只会 `log.error` 然后**当成功继续**。
     * 2) **body 里的 `code`**：200/207 都是 2xx，HTTP 层看不出差别，
     *    必须读 body 才能识别 `207 PARTIAL`（搜索路成功、图谱路失败）。
     */
    public static final class IngestOutcome {
        /** 契约 §1.2 的 code（可能为 null：响应不是我们约定的 JSON） */
        public final Integer code;
        public final int httpStatus;
        public final String body;
        /** OK / PARSE_FAIL / RETRY */
        public final String action;

        IngestOutcome(Integer code, int httpStatus, String body, String action) {
            this.code = code;
            this.httpStatus = httpStatus;
            this.body = body;
            this.action = action;
        }

        public boolean ok() {
            return "OK".equals(action);
        }
    }

    public IngestOutcome ingest(String kb, Long fileId, String doc2mdDir, String fileUrl,
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
        try {
            ResponseEntity<String> response =
                    restTemplate.exchange(remoteV2IngestUrl, HttpMethod.POST, entity, String.class);
            String body = response.getBody();
            Integer code = null;
            if (body != null) {
                JSONObject json = JSONObject.parseObject(body);
                code = json == null ? null : json.getInteger("code");
            }
            String action = classify(response.getStatusCode().value(), code);
            if (!"OK".equals(action)) {
                log.error("V2 摄取未完全成功 action={} http={} code={} body={}",
                        action, response.getStatusCode().value(), code, body);
            }
            return new IngestOutcome(code, response.getStatusCode().value(), body, action);
        } catch (HttpStatusCodeException e) {
            // 4xx/5xx：RestTemplate 抛异常。**必须在这里分类**，不能让它直接冒到调用方
            // 只留一条 log —— 那样"摄取失败"就变成了"不知道发生了什么"。
            String body = e.getResponseBodyAsString();
            Integer code = null;
            try {
                JSONObject json = JSONObject.parseObject(body);
                code = json == null ? null : json.getInteger("code");
            } catch (Exception ignore) {
                // body 不是 JSON：保持 code=null，由 httpStatus 决定动作
            }
            String action = classify(e.getStatusCode().value(), code);
            log.error("V2 摄取失败 action={} http={} code={} body={}",
                    action, e.getStatusCode().value(), code, body);
            return new IngestOutcome(code, e.getStatusCode().value(), body, action);
        } catch (RestClientException e) {
            // 连不上 / 超时：可重试（RETRY），不能当 PARSE_FAIL 把文件判死
            log.error("V2 摄取无法连接 action=RETRY url={} err={}", remoteV2IngestUrl, e.toString());
            return new IngestOutcome(null, 0, null, "RETRY");
        }
    }

    /**
     * 结果分类（契约 §1.2 / §5）。
     *
     * - `200 + code=200` → OK
     * - `200 + code=207`（PARTIAL：搜索路成功、图谱路失败）→ **RETRY**（图还能补）
     * - `4xx`（400 产物不合法 / 409 SOURCE_DIVERGED / 422 前提不满足）→ **PARSE_FAIL**（重试无益）
     * - `5xx`（500 状态损坏 / 502 依赖不可达）→ **RETRY**
     */
    static String classify(int httpStatus, Integer code) {
        if (httpStatus >= 200 && httpStatus < 300) {
            if (code != null && code == 200) {
                return "OK";
            }
            if (code != null && code == 207) {
                return "RETRY";
            }
            return "RETRY";      // 2xx 但没有我们约定的 code：不可信，重试一次再看
        }
        if (httpStatus >= 400 && httpStatus < 500) {
            return "PARSE_FAIL";
        }
        return "RETRY";          // 5xx / 其它
    }
}
