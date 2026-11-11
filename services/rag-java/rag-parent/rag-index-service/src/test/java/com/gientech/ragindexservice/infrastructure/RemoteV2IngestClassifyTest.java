package com.gientech.ragindexservice.infrastructure;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * P4-L13-B · {@link RemoteV2IngestUtils#classify(int, Integer)} 的判定表。
 *
 * <p>为什么必须逐分支测：这个方法是「摄取失败是否被如实回写」的唯一判决点。
 * 判错的后果分两类，都很难在线上发现：
 * <ul>
 *   <li>把 <b>可重试</b>（207 / 5xx / 连不上）判成 {@code PARSE_FAIL} → 文件被判死，不再重试；</li>
 *   <li>把 <b>不可重试</b>（4xx：产物不合法 / SOURCE_DIVERGED / 前提不满足）判成 {@code RETRY}
 *       → 无限重试同一份坏产物。</li>
 * </ul>
 *
 * <p>判定依据是**两层**（实测结论，见 evidence P4-L13B §1）：
 * HTTP 状态码决定「是否抛」（{@code RestTemplate.exchange} 对 4xx/5xx 抛
 * {@code HttpStatusCodeException}），body 的 {@code code} 决定「207 部分成功 vs 200 成功」
 * —— 因为 207 也是 2xx，HTTP 层看不出差别。
 *
 * <p><b>本文件尚未编译/执行</b>（B 段不跑 maven）。它属于 C 段前置：
 * 起服务前应先 `mvn -pl rag-index-service test -Dtest=RemoteV2IngestClassifyTest`。
 */
class RemoteV2IngestClassifyTest {

    private static String classify(int httpStatus, Integer code) {
        return RemoteV2IngestUtils.classify(httpStatus, code);
    }

    @Test
    @DisplayName("2xx + code=200 → OK")
    void okWhenTwoHundredAndCodeTwoHundred() {
        assertEquals("OK", classify(200, 200));
    }

    @Test
    @DisplayName("2xx + code=207 → RETRY（搜索路成功、图谱路失败，图还能补）")
    void retryWhenPartial() {
        // 207 是 2xx：HTTP 层完全看不出差别，只能靠 body code 区分
        assertEquals("RETRY", classify(200, 207));
        assertEquals("RETRY", classify(207, 207));
    }

    @Test
    @DisplayName("2xx 但 code 缺失/未知 → RETRY（不可信，重试一次再看）")
    void retryWhenCodeMissingOnSuccess() {
        assertEquals("RETRY", classify(200, null));
        assertEquals("RETRY", classify(200, 0));
        assertEquals("RETRY", classify(200, 500));
    }

    @Test
    @DisplayName("4xx → PARSE_FAIL（产物/请求不合法，重试无益）")
    void parseFailOnClientError() {
        assertEquals("PARSE_FAIL", classify(400, 400));   // DOC2MD_ARTIFACT_INCOMPLETE
        assertEquals("PARSE_FAIL", classify(409, 409));   // SOURCE_DIVERGED / CURSOR_CONFLICT
        assertEquals("PARSE_FAIL", classify(422, 422));   // NO_BASELINE_SNAPSHOT / KB_REQUIRED
        assertEquals("PARSE_FAIL", classify(404, null));
    }

    @Test
    @DisplayName("5xx → RETRY（依赖不可达/服务端暂时性）")
    void retryOnServerError() {
        assertEquals("RETRY", classify(500, 500));        // KB_STATE_CORRUPT
        assertEquals("RETRY", classify(502, 502));        // INDEX_WRITE_FAILED / GRAPH_UNREACHABLE
        assertEquals("RETRY", classify(503, null));
    }

    @Test
    @DisplayName("连不上（httpStatus=0）→ RETRY，不得判成 PARSE_FAIL 把文件判死")
    void retryWhenUnreachable() {
        assertEquals("RETRY", classify(0, null));
    }

    @Test
    @DisplayName("边界：2xx 边界值 299 仍按成功处理；300/399 归 RETRY")
    void boundaryValues() {
        assertEquals("OK", classify(299, 200));
        assertEquals("RETRY", classify(299, 207));
        assertEquals("RETRY", classify(300, null));
    }
}
