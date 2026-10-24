package com.gientech.ragindexservice.utils;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.plugins.pagination.PageDTO;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragcommon.infrastructure.exception.DomainException;
import com.gientech.ragindexservice.domain.entity.FaqInfo;
import com.google.common.collect.Lists;
import org.apache.commons.lang3.StringUtils;
import org.springframework.http.*;
import org.springframework.web.client.RestTemplate;

import java.util.*;
import java.util.regex.MatchResult;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class Test {

    private RestTemplate restTemplate = new RestTemplate();

    private static final String fileNameRegular = "\\【[^\\【\\】]*\\】|\\[[^\\[\\]]*\\]|\\([^\\(\\)]*\\)|（[^（）]*）|[`~!@#$%^&*()_\\-+\\[\\]=<>?:\"{}|,\\/;'\\\\·~！@#￥%……&*（）.——\\-+={}|〔〕《》？：“”【】、；‘'，。、]|\\s|\\d|(pdf|png|jpeg|jpg|docx|xlsx|pjpg|svg|csv|txt)$";

    static  final String fileNameRegular1 = "[`~!@#$%^&*()_\\-+\\[\\]=<>?:\"{}|,\\/;'\\\\·~！@#￥%……&*（）.——\\-+={}|〔〕《》？：“”【】、；‘'，。、]|(pdf|png|jpeg|jpg|docx|xlsx|pjpg|svg|csv|txt)$";
    static  final String fileNameRegular2 = "\\d+";






    public static void main(String[] args) {

    }

    /**
     * 获取指定字符串中括号内的内容，返回字符串数组
     * @param content
     * @return
     */
    public static Set<String> getBracketContent(String content){
        Set<String> result = new HashSet<>();
        Pattern p =  Pattern.compile("(?<=\\<a id=\")[^\\\">]+");
        Matcher m = p.matcher(content);
        while(m.find()){
            result.add(m.group());
        }
        return result;
    }

    public void test1() {
        Test test = new Test();
        long start = System.currentTimeMillis();
        test.addFAQ();
        System.out.println("时间:" + (System.currentTimeMillis() - start));

        Page<FaqInfo> faqPage = test.faqPageList();
        System.out.println(faqPage.getTotal());
    }

    public Page<FaqInfo> faqPageList() {
        String query = """
                {
                	"index_name": [
                		"faq_相似问5"
                	],
                	"page_no": 1,
                	"page_num": 500,
                	"sort_field": "update_time",
                	"sort_mode": "desc",
                	"condition_json": [
                		{
                			"knowledge_base_name": [
                				"相似问5"
                			]
                		}
                	]
                }
                """;

        String resp = faqPageListEs(query);
        Page<FaqInfo> page = new PageDTO<>();
        List<FaqInfo> records = Lists.newArrayList();
        JSONObject respJson = JSONObject.parseObject(resp);
        if (respJson.getInteger("code").equals(500)) {
            return page;
        }
        if(!Objects.equals(respJson.getInteger("code"),200))
            throw new DomainException(ErrCodeEnum.FAQ_LIST_ERROR);
        JSONObject data = respJson.getJSONObject("data");
        if (Objects.isNull(data))
            return page;
        Integer pageNo = 1;
        Integer pageSize = 500;
        Integer totalCount = data.getInteger("total_count");
        page.setTotal(totalCount);
        page.setCurrent(pageNo);
        page.setSize(pageSize);
        page.setPages((totalCount / pageSize) + ((totalCount % pageSize) > 0 ? 1 : 0));

        JSONArray resultData = data.getJSONArray("result_data");
        if (resultData == null || Objects.isNull(resultData))
            return page;
        resultData.forEach(result -> {
            JSONObject dataJson = (JSONObject) result;
            FaqInfo faq = new FaqInfo();
            JSONObject source = dataJson.getJSONObject("_source");
            faq.setQuestion(source.getString("page_content"));
            JSONObject metadata = source.getJSONObject("metadata");
            if (!Objects.isNull(metadata)) {
                faq.setAnswer(metadata.getString("answer"));
                faq.setPk(metadata.getLong("pk"));
                faq.setRelatedPk(metadata.getLong("related_pk"));
                faq.setStatus(metadata.getInteger("status"));
                String sourceFile = metadata.getString("source");
                faq.setSourceFile(sourceFile);
                faq.setDocumentId(metadata.getLong("document_id"));
                if (StringUtils.isNotBlank(sourceFile))
                    faq.setSourceFileName(sourceFile.substring(sourceFile.lastIndexOf("/") + 1));
            }
            records.add(faq);
        });
        return page;
    }

    public void addFAQ() {
        String faq = """
                {
                 	"document_list": [
                 		{
                 			"page_content": "中国首都在哪",
                 			"metadata": {
                 				"source": "",
                 				"knowledge_base_name": "相似问5",
                 				"related_pk": 1849010080118800385,
                 				"pk": 1849010080118800386,
                 				"answer": "北京"
                 			}
                 		}
                 	],
                 	"index_name": "faq_相似问5"
                 }
                """;
        faqSaveEs(faq);
    }

    public String faqPageListEs(String requestPara) {
        String remoteFaqPageListEsUrl = "http://10.15.12.12:19527/search_by_page";
        return doExchange(requestPara, remoteFaqPageListEsUrl, HttpMethod.POST).getBody();
    }

    public String faqSaveEs(String requestPara) {
        String remoteFaqSaveEsUrl = "http://10.15.12.12:19527/insert_fulltext_documents";
        return doExchange(requestPara, remoteFaqSaveEsUrl, HttpMethod.POST).getBody();
    }

    private ResponseEntity<String> doExchange(String param, String url, HttpMethod httpMethod) {

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Object> requestEntity = new HttpEntity<>(param, headers);
//        log.info("远程url:{},请求方式:{},请求参数:{}", url, httpMethod.name(), param);
        ResponseEntity<String> response = restTemplate.exchange(url, httpMethod, requestEntity, String.class);
//        log.info("远程服务响应结果:{}", JSONObject.toJSONString(response.getBody()));
        HttpStatusCode httpStatusCode = response.getStatusCode();
        if (200 != httpStatusCode.value()) {
            throw new ApplicationException(ErrCodeEnum.FILE_PARSE_ERROR);
        }
        return response;
    }
}
