package com.gientech.ragcommon.global;

import com.alibaba.cloud.commons.lang.StringUtils;
import jakarta.servlet.http.HttpServletRequest;
import lombok.Data;

/**
 * @author chenjuan
 */
@Data
public class OpenApiHeader {
    private String platform;
    private String userName;
    private String userId;

    public static final String PLATFORM_HEADER = "X-Platform";
    public static final String USER_ID_HEADER = "X-UserID";
    public static final String USER_NAME_HEADER = "X-UserName";
    public static final String AUTHORIZATION = "Authorization";

    public static OpenApiHeader getHeaders(HttpServletRequest request){
        OpenApiHeader openApiHeader = new OpenApiHeader();
        openApiHeader.setPlatform(StringUtils.isBlank(request.getHeader(PLATFORM_HEADER)) ? "rag-qa" : request.getHeader(PLATFORM_HEADER));
        openApiHeader.setUserId(request.getHeader(USER_ID_HEADER));
        openApiHeader.setUserName(request.getHeader(USER_NAME_HEADER));
        return openApiHeader;
    }

    public static String getPlatformHeader(HttpServletRequest request){
        return StringUtils.isBlank(request.getHeader(PLATFORM_HEADER))?"rag-qa":request.getHeader(PLATFORM_HEADER);
    }
}
