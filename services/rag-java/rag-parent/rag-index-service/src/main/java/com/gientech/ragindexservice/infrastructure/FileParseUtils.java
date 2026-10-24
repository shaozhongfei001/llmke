package com.gientech.ragindexservice.infrastructure;

import cn.hutool.core.io.FileUtil;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.gientech.ragcommon.infrastructure.utils.CharsetEncodeUtils;
import com.opencsv.CSVReader;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.poi.ss.usermodel.Row;
import org.apache.poi.ss.usermodel.Sheet;
import org.apache.poi.ss.usermodel.Workbook;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.springframework.core.io.Resource;
import org.springframework.core.io.UrlResource;
import org.springframework.stereotype.Component;
import org.springframework.util.CollectionUtils;

import java.io.*;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Component
@Slf4j
public class FileParseUtils {

    public List<Map<String, Object>> getFaqs(String filePath) {
        if (StringUtils.isEmpty(filePath))
            return null;
        String fileType = filePath.substring(filePath.lastIndexOf(".") + 1);

        switch (fileType) {
            case "txt":
                return txtFileParse(filePath);
            case "csv":
                return csvFileParse(filePath);
            case "xlsx":
                return xlsxFileParse(filePath);
            default:
                log.error("暂不支持的文件类型:{}", fileType);
                return null;
        }
    }

    private List<Map<String, Object>> xlsxFileParse(String filePath) {
        List<Map<String, Object>> resList = new ArrayList<>();
        InputStream is = null;
        try {
            Resource resource = new UrlResource(filePath);
            is = resource.getInputStream();
            Workbook workbook = new XSSFWorkbook(is);
            Sheet sheet = workbook.getSheetAt(0);
            for (Row row : sheet) {
                Map<String, Object> dataMap = new HashMap<>();
                String question =row.getCell(0).getStringCellValue();
                String answer =row.getCell(1).getStringCellValue();
                if(StringUtils.isEmpty(question) || StringUtils.isEmpty(answer))
                    continue;
                dataMap.put("question", question);
                dataMap.put("answer", answer);
                resList.add(dataMap);
            }
        } catch (Exception e) {
            log.error("读取【" + filePath + "】文件失败,失败原因：【" + e.getMessage() + "】");
        } finally {
            if (is != null) {
                try {
                    is.close();
                } catch (IOException e) {
                    log.error("关闭流失败,失败原因：【" + e.getMessage() + "】");
                }
            }
        }
        return resList;
    }

    private List<Map<String, Object>> csvFileParse(String filePath) {
        CSVReader reader = null;
        InputStream inputStream = null;
        BufferedInputStream bufferedInputStream = null;
        List<Map<String, Object>> resList = new ArrayList<>();
        try {
            Resource resource = new UrlResource(filePath);
            inputStream = resource.getInputStream();
            bufferedInputStream = new BufferedInputStream(inputStream);
            String charset = CharsetEncodeUtils.charsetEncode(bufferedInputStream);
            reader = new CSVReader(new InputStreamReader(resource.getInputStream(), charset));
            List<String[]> dataStrs = reader.readAll();
            for (String[] dataStr : dataStrs) {
                Map<String, Object> dataMap = new HashMap<>();
                String question = dataStr[0];
                String answer = dataStr[1];
                if(StringUtils.isEmpty(question) || StringUtils.isEmpty(answer))
                    continue;
                dataMap.put("question", question);
                dataMap.put("answer", answer);
                resList.add(dataMap);
            }
        } catch (Exception e) {
            log.error("读取【" + filePath + "】文件失败,失败原因：【" + e.getMessage() + "】");
        } finally {
            if (reader != null) {
                try {
                    reader.close();
                } catch (IOException e) {
                    log.error("关闭流失败,失败原因：【" + e.getMessage() + "】");
                }
            }

            if (inputStream != null) {
                try {
                    inputStream.close();
                } catch (IOException e) {
                    log.error("关闭流失败,失败原因：【" + e.getMessage() + "】");
                }
            }

            if (bufferedInputStream != null) {
                try {
                    bufferedInputStream.close();
                } catch (IOException e) {
                    log.error("关闭流失败,失败原因：【" + e.getMessage() + "】");
                }
            }
        }
        return resList;

    }

    private List<Map<String, Object>> txtFileParse(String filePath) {
        String jsonString = null;
        InputStream in = null;
        try {
            Resource resource = new UrlResource(filePath);
            in = resource.getInputStream();
            File tempFile = FileUtil.createTempFile(null);
            FileUtils.copyInputStreamToFile(in, tempFile);
            jsonString = FileUtil.readString(tempFile, "UTF-8");
            FileUtil.del(tempFile);
        } catch (IOException e) {
            System.out.println(e);
        } finally {
            try {
                in.close();
            } catch (IOException e) {
                log.error("关闭流异常:" + e.getMessage());
            }
        }
        List<JSONObject> dataList = JSON.parseArray(jsonString, JSONObject.class);
        if (CollectionUtils.isEmpty(dataList))
            return null;
        List<Map<String, Object>> resList = new ArrayList<>(dataList.size());
        dataList.forEach(data -> {
            Map<String, Object> faqMap = new HashMap<>();
            String question = data.getString("question");
            String answer = data.getString("answer");
            if(StringUtils.isNotEmpty(question) && StringUtils.isNotEmpty(answer)){
                faqMap.put("question", data.getString("question"));
                faqMap.put("answer", data.getString("answer"));
                resList.add(faqMap);
            }
        });
        return resList;
    }

    public static void main(String[] args) throws Exception {
        FileParseUtils fileParseUtils = new FileParseUtils();
//        List<Map<String, Object>> faqs = fileParseUtils.getFaqs("http://10.64.7.145:9000/dev-rag-data/aa11/FAQ模版1000-GBK.csv");
//        List<Map<String, Object>> faqs = fileParseUtils.getFaqs("http://10.64.7.145:9000/dev-rag-data/aa11/FAQ模版1000-UTF-8.csv");
//        List<Map<String, Object>> faqs = fileParseUtils.getFaqs("http://10.15.12.12:9000/dev-rag-data/召回知识库3/faq/FAQ模版 (1).xlsx");
//        List<Map<String, Object>> faqs = fileParseUtils.getFaqs("http://10.15.12.12:9000/dev-rag-data/召回知识库3/faq/FAQ模版.xlsx");
        List<Map<String, Object>> faqs = fileParseUtils.getFaqs("http://10.15.12.12:9000/dev-rag-data/召回知识库4/faq/FAQ  (1).txt");

        for (Map<String, Object> faq : faqs) {

            System.out.println(JSON.toJSONString(faq));
        }
    }
}
