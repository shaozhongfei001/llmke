package com.gientech.ragcommon.global;

import lombok.Getter;
import lombok.Setter;
import lombok.ToString;

/**
 * @Description:
 * @Author: ws
 * @Date: 2024/5/27 15:43
 */
@Setter
@Getter
@ToString
public class CommonResponse<T> {

    /**
     * 是否成功
     */
    private Boolean success;

    /**
     * 错误信息
     */
    private String errorMsg;

    /**
     * 错误编码
     */
    private String errorCode;

    /**
     * 返回数据
     */
    private T data;

    public static <T> CommonResponse<T> success (T data){
        CommonResponse<T> response = new CommonResponse<>();
        response.setSuccess(true);
        response.setData(data);
        return response;
    }

    public static <T> CommonResponse<T> fail (String errorMsg){
        CommonResponse<T> response = new CommonResponse<T>();
        response.setSuccess(false);
        response.setErrorMsg(errorMsg);
        response.setData(null);
        return response;
    }

    public static <T> CommonResponse<T> fail (String errorMsg, String errorCode){
        CommonResponse<T> response = new CommonResponse<T>();
        response.setSuccess(false);
        response.setErrorMsg(errorMsg);
        response.setErrorCode(errorCode);
        response.setData(null);
        return response;
    }

    public static <T> CommonResponse<T> fail (ErrCodeEnum errCodeEnum){
        CommonResponse<T> response = new CommonResponse<T>();
        response.setSuccess(false);
        response.setErrorMsg(errCodeEnum.getErrMsg());
        response.setErrorCode(errCodeEnum.getErrCode());
        response.setData(null);
        return response;
    }

}
