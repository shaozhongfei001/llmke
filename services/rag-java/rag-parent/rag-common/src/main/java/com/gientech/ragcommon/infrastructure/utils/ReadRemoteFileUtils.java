package com.gientech.ragcommon.infrastructure.utils;

import lombok.extern.slf4j.Slf4j;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.URL;

@Slf4j
public class ReadRemoteFileUtils {

    public static String readTxt(String filePath){
        StringBuilder txtContent = new StringBuilder();
        try {
            URL url = new URL(filePath);
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(url.openStream()))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    txtContent.append(line).append("\n");
                }
            }
        } catch (Exception e) {
            log.error("读取文件内容失败,filePath:{},异常原因:{}",filePath,e.getMessage());
            return null;
        }
        return txtContent.toString();
    }

    public static void main(String[] args) {
        System.out.println(ReadRemoteFileUtils.readTxt("http://10.15.12.13:9000/dev-rag-data/文档内容/文档内容_医疗图谱test/V0/医疗图谱test4.txt"));
    }
}