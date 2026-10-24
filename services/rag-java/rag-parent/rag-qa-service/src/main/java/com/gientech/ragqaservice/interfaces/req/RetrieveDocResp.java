package com.gientech.ragqaservice.interfaces.req;


import com.gientech.ragqaservice.interfaces.dto.RetrieveData;
import lombok.Data;

/**
 * @author chenjuan
 * @date 2025/6/24 14:20
 */
@Data
public class RetrieveDocResp {
    private Integer code;
    private String msg;
    private RetrieveData data;
}
