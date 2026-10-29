package com.gientech.ragindexservice.infrastructure;

import com.alibaba.fastjson2.JSONObject;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

@Slf4j
@Component
public class RemoteGraphUtils {

    private RestTemplate restTemplate = new RestTemplate();

    /**
     * 图解析
     */
    @Value("${remote.generate-graph.url}")
    private String remoteGenerateGraphUrl;

    @Value("${remote.generate-community.url:}")
    private String remoteGenerateCommunityUrl;

    /**
     * 图删除(删除整个图空间或者删除图空间下的某个文件中的数据)
     */
    @Value("${remote.del-graph-space.url}")
    private String remoteDelGraphSpaceUrl;

    /**
     * milvus中删除图实体表的接口
     */
    @Value("${remote.del-graph-entity.url}")
    private String remoteDelGraphEntityUrl;

    /**
     * 图解析
     *
     * @param requestPara
     * @return
     */
    public String delSpace(String requestPara) {
        return doExchange(requestPara, remoteDelGraphSpaceUrl, HttpMethod.POST).getBody();
    }

    public String generateGraph(String requestPara) {
        return doExchange(requestPara, remoteGenerateGraphUrl, HttpMethod.POST).getBody();
    }

    /** R15 W03：图数据变更后重建社区摘要；未配置地址时返回 null（保持旧行为）。 */
    public String generateCommunity(String requestPara) {
        if (remoteGenerateCommunityUrl == null || remoteGenerateCommunityUrl.trim().isEmpty()) {
            return null;
        }
        return doExchange(requestPara, remoteGenerateCommunityUrl, HttpMethod.POST).getBody();
    }

    public String delSpaceEntity(String requestPara) {
        return doExchange(requestPara, remoteDelGraphEntityUrl, HttpMethod.POST).getBody();
    }

    private ResponseEntity<String> doExchange(String param, String url, HttpMethod httpMethod) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Object> requestEntity = new HttpEntity<>(param, headers);
        log.info("远程url:{},请求方式:{},请求参数:{}", url, httpMethod.name(), param);
        ResponseEntity<String> response = restTemplate.exchange(url, httpMethod, requestEntity, String.class);
        log.info("远程url:{},响应结果:{}", url, JSONObject.toJSONString(response.getBody()));
        HttpStatusCode httpStatusCode = response.getStatusCode();
        if (200 != httpStatusCode.value()) {
            throw new ApplicationException(ErrCodeEnum.FILE_PARSE_ERROR);
        }
        return response;
    }
}
