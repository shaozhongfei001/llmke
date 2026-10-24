package com.gientech.ragcommon.index.parameter;

import com.alibaba.fastjson2.annotation.JSONField;
import lombok.Data;

@Data
public class FileMultiversion {

    /**
     * 文件id
     */
    private String id;

    /**
     * 文件名称
     */
    private String name;

    /**
     * 文件集群组id，算法端根据文件内容生成
     */
    @JSONField(name = "group_id")
    private String groupId;

    /**
     * 文件修订时间
     */
    @JSONField(name = "version_date")
    private String versionDate;
}
