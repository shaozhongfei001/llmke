package com.gientech.ragqaservice.infrastructure;

import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import lombok.extern.slf4j.Slf4j;
import okhttp3.*;
import org.apache.commons.lang3.StringUtils;
import org.springframework.http.*;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Component
@Slf4j
public class HttpUtils {

    private RestTemplate restTemplate = new RestTemplate();

    public ResponseEntity<String> doExchange(String param, String url, HttpMethod httpMethod) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Object> requestEntity = new HttpEntity<>(param, headers);
        log.info("远程url:{},请求方式:{},请求参数:{}", url, httpMethod.name(), param);
        ResponseEntity<String> response = restTemplate.exchange(url, httpMethod, requestEntity, String.class);
        log.info("远程url:{},响应结果:{}",url, JSONObject.toJSONString(response.getBody()));
        HttpStatusCode httpStatusCode = response.getStatusCode();
        if (200 != httpStatusCode.value()) {
            throw new ApplicationException(ErrCodeEnum.FILE_PARSE_ERROR);
        }
        return response;
    }

    public static <T> T sendPostRequest(String appKey, String url, Map<String, Object> paramsMap, Class<T> tClass) {
        HttpHeaders headers = new HttpHeaders();
        // 以JSON的方式提交
        headers.setContentType(MediaType.APPLICATION_JSON);
        if(StringUtils.isNotEmpty(appKey))
            headers.set("appKey", appKey); //MdNTpGPBnGvEFmytrYpA

        Map<String, Object> map = new HashMap<>();
        for (String key : paramsMap.keySet()) {
            map.put(key, paramsMap.get(key));
        }
        //将请求头部和参数合成一个请求
        HttpEntity<Map> requestEntity = new HttpEntity<>(map, headers);

        //执行HTTP请求，将返回的结构使用ResultVO类格式化
        log.info("开始请求URL：" + url + ", 参数：" + requestEntity);
        try {
            ResponseEntity<com.alibaba.fastjson.JSONObject> response = new RestTemplate().exchange(url, HttpMethod.POST, requestEntity, com.alibaba.fastjson.JSONObject.class);
            if (response.getStatusCode().value() != HttpStatus.OK.value()) {
                throw new RuntimeException("请求：" + url + "异常，响应码：" + response.getStatusCode());
            }
            String responseJSON = com.alibaba.fastjson.JSONObject.toJSONString(response.getBody());
            log.info("返回报文：{}", responseJSON);
            return com.alibaba.fastjson.JSONObject.parseObject(responseJSON, tClass);
        } catch (Exception e) {
            log.error("请求出错", e);
            if (e instanceof ResourceAccessException) {
                throw (ResourceAccessException) e;
            }
            throw new RuntimeException(e);
        }
    }

    public static Map<String, Object> sendPostRequestForStream(String appKey, String url, String params) {
        OkHttpClient client = new OkHttpClient.Builder()
                .readTimeout(0, TimeUnit.MILLISECONDS) // 设置无限读取超时，因为SSE是长连接
                .build();

        RequestBody jsonBody = RequestBody.create(okhttp3.MediaType.parse("application/json; charset=utf-8"), params);
        Request request = new Request.Builder()
                .url(url)
                .post(jsonBody)
                .header("Accept", "text/event-stream")
                .header("appKey", appKey)
                .build();
        StringBuilder stringBuilder = new StringBuilder();
        Map<String, Object> map = new HashMap<>();

        try (Response response = client.newCall(request).execute()) {
            if (!response.isSuccessful()) {
                throw new IOException("Unexpected code " + response);
            }

            // 获取响应体并读取流
            ResponseBody responseBody = response.body();
            StringBuilder stringBuilderTemp = new StringBuilder();
            try (java.io.Reader reader = responseBody.charStream()) {
                char[] buffer = new char[1024];
                int bytesRead;
                while ((bytesRead = reader.read(buffer)) != -1) {
                    String data = new String(buffer, 0, bytesRead);
                    stringBuilderTemp.append(data);
                }
            }
        } catch (IOException e) {

        }
        map.put("content", stringBuilder.toString());
        return map;
    }
}
