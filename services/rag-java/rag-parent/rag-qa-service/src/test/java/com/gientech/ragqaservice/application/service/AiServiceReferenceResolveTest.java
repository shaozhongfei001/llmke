package com.gientech.ragqaservice.application.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.gientech.ragcommon.index.dto.KnowledgeBaseFileDTO;
import com.gientech.ragqaservice.application.remote.KbClient;
import com.gientech.ragqaservice.application.service.impl.AiServiceImpl;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.lang.reflect.Method;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

/**
 * T-A1 / D7：global 分支的引用必须能靠 file_id 反查到可打开的原文路径。
 *
 * 为什么单独测这一个方法：`question_re` 的 global 分支原来把检索侧 documents_list 原样下发，
 * 里面只有 file_id、没有 source，页面点引用打不开原文。修法是复用 publicQuestion 的
 * R13-GRAPH-11 反查（已抽成 resolveSourceByFileId / enrichReferenceSources）。
 * 这条测试直接打私有方法，断言三件在线上会要命的事：
 * ① 有 convertedFilePath 时必须补出 source 且归一成桶内对象键；
 * ② 非数字 file_id（演示语料 F003 这类）不得抛异常，也不得拼出 "null" 链接；
 * ③ 输入不是 JSON 数组时原样返回（引用形状不止一种，不能因此 500）。
 */
class AiServiceReferenceResolveTest {

    private static final String MINIO_URL =
            "http://127.0.0.1:19000/r12-rag/kb_1002/docx-plain.docx/V0/docx-plain.docx";
    private static final String BUCKET_KEY =
            "r12-rag/kb_1002/docx-plain.docx/V0/docx-plain.docx";

    private AiServiceImpl service;
    private Method enrich;

    @BeforeEach
    void setUp() throws Exception {
        service = new AiServiceImpl();

        KnowledgeBaseFileDTO file = new KnowledgeBaseFileDTO();
        file.setId(999017L);
        file.setFileName("docx-plain.docx");
        file.setConvertedFilePath(MINIO_URL);

        KbClient kbClient = mock(KbClient.class);
        when(kbClient.getByIds(anyList())).thenReturn(Collections.singletonList(file));
        ReflectionTestUtils.setField(service, "kbClient", kbClient);

        enrich = AiServiceImpl.class.getDeclaredMethod("enrichReferenceSources", String.class);
        enrich.setAccessible(true);
    }

    private String invoke(String reference) throws Exception {
        return (String) enrich.invoke(service, reference);
    }

    @Test
    void globalReferenceWithOnlyFileIdBecomesOpenableSource() throws Exception {
        String reference = "[{\"page_content\":\"单户最高授信额度为5000万元\","
                + "\"metadata\":{\"file_id\":\"999017\",\"community\":\"c-3\"},\"type\":\"global\"}]";

        JSONArray out = JSON.parseArray(invoke(reference));
        assertEquals(1, out.size());
        JSONObject metadata = out.getJSONObject(0).getJSONObject("metadata");
        assertNotNull(metadata);
        // 键必须是桶内对象键：前端是 /minio/${source}，下发绝对 URL 会拼成 /minio/http://...
        assertEquals(BUCKET_KEY, metadata.getString("source"));
        assertEquals("docx-plain.docx", metadata.getString("title"));
        assertEquals(999017L, metadata.getLongValue("file_id"));
        // 原有字段不能被反查过程改掉
        assertEquals("c-3", metadata.getString("community"));
    }

    @Test
    void nonNumericFileIdDoesNotThrowAndDoesNotFakeSource() throws Exception {
        String reference = "[{\"page_content\":\"演示语料\",\"metadata\":{\"file_id\":\"F003\"}}]";

        JSONArray out = JSON.parseArray(invoke(reference));
        JSONObject metadata = out.getJSONObject(0).getJSONObject("metadata");
        assertEquals("", metadata.getString("source"), "解析不到就必须留空，不能拼 null 假链接");
    }

    @Test
    void nonArrayReferenceIsReturnedAsIs() throws Exception {
        String notArray = "{\"documents_list\":[]}";
        String out = invoke(notArray);
        assertSame(notArray, out, "不是数组就原样返回，不能 500 也不能丢引用");
    }

    @Test
    void blankReferenceIsReturnedAsIs() throws Exception {
        assertTrue(invoke("") == null || invoke("").isEmpty());
    }
}
