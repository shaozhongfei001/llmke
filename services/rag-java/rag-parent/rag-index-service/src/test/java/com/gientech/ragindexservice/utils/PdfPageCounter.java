package com.gientech.ragindexservice.utils;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import org.apache.pdfbox.pdmodel.PDDocument;
import java.io.IOException;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.List;

public class PdfPageCounter {
    public static void main(String[] args) {
        try {
            String path = "http://10.15.12.13:9000/dev-rag-data/富文本3/富文本3_轴承工作原理组件及接触角/V0/轴承工作原理、组件及接触角.pdf";
            String path2 = "http://10.15.12.13:9000/dev-rag-data/富文本3/富文本3_d湛江设备运维故障诊断及维修方案集装箱岸边起重机振华岸桥培训资料第五节应急故障处理/V0/d湛江-设备运维-故障诊断及维修方案-集装箱岸边起重机-振华岸桥培训资料-5第五节 应急故障处理.pdf";
            String path3 = "http://10.15.12.13:9000/dev-rag-data/富文本3/富文本3_维修方案/V0/维修方案.pdf";
            String path4 = "http://10.15.12.13:9000/dev-rag-data/富文本3/富文本3_维修方案/V0/维修  方案.pdf";

            URL url = new URL(path4);
            PDDocument document = PDDocument.load(url.openStream());
            int numberOfPages = document.getNumberOfPages();
            System.out.println(numberOfPages);
            document.close();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}