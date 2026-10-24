package com.gientech.ragindexservice.application.remote;

import com.gientech.ragcommon.index.request.PyLabelReq;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.List;

/**
 * @author chenjuan
 * @date 2025/5/9 17:25
 */
@SpringBootTest
public class PyClientTest {
    @Autowired
    private PyMilvusClient pyMilvusClient;
    @Test
    public void test() {
        PyLabelReq pyLabelReq = new PyLabelReq();
        pyLabelReq.setColName("labels");
        pyLabelReq.setColValue(List.of("啊啊啊啊","90_啥事"));
        pyLabelReq.setFileIds(List.of("428074930101317517"));
        pyLabelReq.setIndexName("测试0428-yu");
//        PyLabelResponse pyLabelResponse = pyMilvusClient.updateById(pyLabelReq);
//        System.out.println(JSON.toJSONString(pyLabelResponse));
    }
}
