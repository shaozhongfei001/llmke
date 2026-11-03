import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.gientech.ragcommon.index.dto.KnowledgeBaseFileDTO;
import com.gientech.ragqaservice.application.remote.KbClient;
import com.gientech.ragqaservice.application.service.impl.AiServiceImpl;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.Collections;
import java.util.List;

/**
 * T-A1 运行时验证（不依赖 maven-surefire：离线仓库里 surefire 2.12.4 缺 junit3 provider）。
 * 用动态代理把 KbClient 桩住，直接打 AiServiceImpl 的私有 enrichReferenceSources，
 * 断言"只有 file_id 的 global 引用"能被补成可打开原文的 source。
 */
public class T {

    private static int fail = 0;

    public static void main(String[] args) throws Exception {
        String minio = "http://127.0.0.1:19000/r12-rag/kb_1002/docx-plain.docx/V0/docx-plain.docx";
        String bucket = "r12-rag/kb_1002/docx-plain.docx/V0/docx-plain.docx";

        KnowledgeBaseFileDTO file = new KnowledgeBaseFileDTO();
        file.setId(999017L);
        file.setFileName("docx-plain.docx");
        file.setConvertedFilePath(minio);

        KbClient stub = (KbClient) Proxy.newProxyInstance(
                T.class.getClassLoader(), new Class[]{KbClient.class},
                (p, m, a) -> {
                    if ("getByIds".equals(m.getName())) {
                        List<Long> ids = (List<Long>) a[0];
                        if (ids.contains(999017L)) {
                            return Collections.singletonList(file);
                        }
                        return Collections.emptyList();
                    }
                    return null;
                });

        AiServiceImpl svc = new AiServiceImpl();
        Field f = AiServiceImpl.class.getDeclaredField("kbClient");
        f.setAccessible(true);
        f.set(svc, stub);

        // toBucketKey 需要 storageProperties：把默认存储的桶名/endPoint 桩住（与真实环境一致）
        Class<?> spClass = Class.forName("com.gientech.start.storage.properties.StorageProperties");
        Class<?> dspClass = spClass.getMethod("getDefaultStorageProperties").getReturnType();
        Object dsp = org.mockito.Mockito.mock(dspClass, inv -> {
            switch (inv.getMethod().getName()) {
                case "getBucketName":
                    return "r12-rag";
                case "getEndPoint":
                    return "http://127.0.0.1:19000";
                default:
                    return null;
            }
        });
        Object sp = org.mockito.Mockito.mock(spClass, inv ->
                "getDefaultStorageProperties".equals(inv.getMethod().getName()) ? dsp : null);
        Field spf = AiServiceImpl.class.getDeclaredField("storageProperties");
        spf.setAccessible(true);
        spf.set(svc, sp);

        Method enrich = AiServiceImpl.class.getDeclaredMethod("enrichReferenceSources", String.class);
        enrich.setAccessible(true);

        // ① 真实上传文件的 file_id → 桶内对象键
        String ref = "[{\"page_content\":\"单户最高授信额度为5000万元\","
                + "\"metadata\":{\"file_id\":\"999017\",\"community\":\"c-3\"},\"type\":\"global\"}]";
        String out = (String) enrich.invoke(svc, ref);
        JSONArray arr = JSON.parseArray(out);
        JSONObject md = arr.getJSONObject(0).getJSONObject("metadata");
        check("① source=桶内对象键", bucket.equals(md.getString("source")), md.getString("source"));
        check("① title 回填", "docx-plain.docx".equals(md.getString("title")), md.getString("title"));
        check("① file_id 归一", md.getLongValue("file_id") == 999017L, md.getString("file_id"));
        check("① 其它字段未被动", "c-3".equals(md.getString("community")), md.getString("community"));

        // ② 非数字 file_id：不抛异常、不留假链接
        String out2 = (String) enrich.invoke(svc,
                "[{\"page_content\":\"演示语料\",\"metadata\":{\"file_id\":\"F003\"}}]");
        JSONObject md2 = JSON.parseArray(out2).getJSONObject(0).getJSONObject("metadata");
        check("② 非法 id → source 为空", "".equals(md2.getString("source")), md2.getString("source"));

        // ③ 非数组原样返回
        String notArray = "{\"documents_list\":[]}";
        check("③ 非数组原样返回", notArray.equals(enrich.invoke(svc, notArray)), "checked");

        // ④ 空引用原样返回
        Object blank = enrich.invoke(svc, "");
        check("④ 空引用", blank == null || "".equals(blank), String.valueOf(blank));

        System.out.println(fail == 0 ? "ALL PASS (4/4)" : ("FAIL count=" + fail));
        if (fail != 0) {
            System.exit(1);
        }
    }

    private static void check(String name, boolean ok, String got) {
        System.out.println((ok ? "PASS " : "FAIL ") + name + (ok ? "" : ("  got=" + got)));
        if (!ok) {
            fail++;
        }
    }
}
