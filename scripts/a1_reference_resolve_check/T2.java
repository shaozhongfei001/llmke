import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.gientech.ragcommon.index.dto.KnowledgeBaseFileDTO;
import com.gientech.ragqaservice.application.remote.KbClient;
import com.gientech.ragqaservice.application.service.impl.AiServiceImpl;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.List;

/**
 * T-A1 真实数据验证：输入不是构造的，而是
 *   ① kb_9 里真实上传并已解析的文档 id=333（docx-table.docx）的产品解析块建图；
 *   ② 18096 /v2/graph/global 的真实响应；
 *   ③ 经 retrieval_shim 的 _global_documents/_to_document 映射出的 Java 实际输入形状。
 * KbClient 桩返回的是 MySQL 里该行的真实 converted_file_path（脚本入参给出，不编造）。
 */
public class T2 {

    private static int fail = 0;

    public static void main(String[] args) throws Exception {
        String docsJson = new String(Files.readAllBytes(Path.of("/tmp/a1-documents_list.json")),
                StandardCharsets.UTF_8);
        long fileId = Long.parseLong(args[0]);            // 333
        String fileName = args[1];                        // docx-table.docx
        String converted = args[2];                       // http://127.0.0.1:19000/r12-rag/kb_9/docx-table.docx/V0/docx-table.docx
        String expectedKey = args[3];                     // r12-rag/kb_9/docx-table.docx/V0/docx-table.docx

        KnowledgeBaseFileDTO file = new KnowledgeBaseFileDTO();
        file.setId(fileId);
        file.setFileName(fileName);
        file.setConvertedFilePath(converted);

        KbClient stub = (KbClient) Proxy.newProxyInstance(
                T2.class.getClassLoader(), new Class[]{KbClient.class},
                (p, m, a) -> {
                    if ("getByIds".equals(m.getName())) {
                        List<Long> ids = (List<Long>) a[0];
                        return ids.contains(fileId) ? Collections.singletonList(file)
                                                    : Collections.emptyList();
                    }
                    return null;
                });

        AiServiceImpl svc = new AiServiceImpl();
        set(svc, "kbClient", stub);

        Class<?> spClass = Class.forName("com.gientech.start.storage.properties.StorageProperties");
        Class<?> dspClass = spClass.getMethod("getDefaultStorageProperties").getReturnType();
        Object dsp = org.mockito.Mockito.mock(dspClass, inv -> {
            switch (inv.getMethod().getName()) {
                case "getBucketName": return "r12-rag";
                case "getEndPoint":   return "http://127.0.0.1:19000";
                default: return null;
            }
        });
        Object sp = org.mockito.Mockito.mock(spClass, inv ->
                "getDefaultStorageProperties".equals(inv.getMethod().getName()) ? dsp : null);
        set(svc, "storageProperties", sp);

        Method enrich = AiServiceImpl.class.getDeclaredMethod("enrichReferenceSources", String.class);
        enrich.setAccessible(true);

        System.out.println("输入（Java 实际收到的 documents_list，前 260 字）：");
        System.out.println("  " + docsJson.replace("\n", " ").substring(0, Math.min(260, docsJson.length())));
        JSONArray before = JSON.parseArray(docsJson);
        String beforeSource = before.getJSONObject(0).getJSONObject("metadata").getString("source");

        String after = (String) enrich.invoke(svc, docsJson);
        JSONArray arr = JSON.parseArray(after);
        JSONObject md = arr.getJSONObject(0).getJSONObject("metadata");

        System.out.println("输出 metadata：");
        System.out.println("  source=" + md.getString("source"));
        System.out.println("  file_id=" + md.getLongValue("file_id") + " title=" + md.getString("title")
                + " locator=" + md.getString("locator") + " community=" + md.getString("community"));

        check("改前 source 为空（正是 D7 缺陷）", beforeSource == null || beforeSource.isEmpty(),
                String.valueOf(beforeSource));
        check("改后 source = 真实文件的桶内对象键", expectedKey.equals(md.getString("source")),
                md.getString("source"));
        check("file_id 仍是真实上传文件的 id", md.getLongValue("file_id") == fileId,
                md.getString("file_id"));
        check("title 回填为真实文件名", fileName.equals(md.getString("title")), md.getString("title"));
        check("locator 未被破坏（可高亮）", "page=1;chunk=0".equals(md.getString("locator")),
                md.getString("locator"));
        check("community 未被破坏", "c-2".equals(md.getString("community")), md.getString("community"));

        System.out.println(fail == 0 ? "ALL PASS (6/6)" : ("FAIL count=" + fail));
        if (fail != 0) {
            System.exit(1);
        }
    }

    private static void set(Object target, String field, Object value) throws Exception {
        Field f = AiServiceImpl.class.getDeclaredField(field);
        f.setAccessible(true);
        f.set(target, value);
    }

    private static void check(String name, boolean ok, String got) {
        System.out.println((ok ? "PASS " : "FAIL ") + name + (ok ? "" : ("  got=" + got)));
        if (!ok) {
            fail++;
        }
    }
}
