package com.gientech.ragqaservice.interfaces.resp;

import lombok.Data;

/**
 * @author: shirleychen
 * @date 2025/9/2 13:26
 * @description
 */
@Data
public class RetrieveSqlDataReference {
    private String filePath;
    private String tag;
    private String reference;
}
