package com.gientech.ragcommon.infrastructure.emuns;

public interface RedisKeyEnums {

    /**
     * 登录验证码前缀
     */
    String CAPTCHA_PREFIX = "captcha:";

    /**
     * 用户token前缀
     */
    String USER_TOKEN_PREFIX = "user:token:";

    /**
     * 用户资源
     */
    String AUTH_USER_RESOURCE = "resourcesOfUsers:";

    /**
     *用户权限菜单
     */
    String AUTH_USER_MENU = "menusOfUser:";

    /**
     * 验证码
     */
    String REGISTER_CAPTCHA_PREFIX = "captcha:register:";

    /**
     * 导入用户验证失败的数据
     */
    String USER_IMPORT_DATA_ERROR_PREFIX = "user:import:error:";

    String DEPT_IMPORT_DATA_ERROR_PREFIX = "dept:import:error:";


    /**
     *  ============index服务相关===============
     */

    /**
     * 文件已经抽取问答对的数量
     */
    String FILE_EXTRACTED_NUMS_PREFIX = "faq:nums:";

    /**
     * 用户搜索前缀
     */
    String USER_SEARCH_PREFIX = "user:search:";

    /**
     * 文件多版本
     */
    String FILE_MULTI_VERSION_PREFIX = "multi:version:";


    /**
     * =============知识图谱相关的key==============
     */

    /**
     * 子图的前缀
     */
    String SUB_GRAPH_PREFIX = "subGraph:";

    /**
     * 图统计
     */
    String GRAPH_STATISTICS_PREFIX = "graphStatistic:";

}
