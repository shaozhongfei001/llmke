package com.gientech.ragcommon.sensitive.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class SensitiveWordHitDTO {

    /*
    序号 id
    */
    private Integer id;

    /*
     敏感词，如：最好
     */
    private String word;

    /*
    感词上下文（前端反显使用），如：牙膏全球最好，刷完就白了
     */
    private String context;
}
