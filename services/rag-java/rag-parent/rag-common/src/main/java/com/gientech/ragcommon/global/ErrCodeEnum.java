package com.gientech.ragcommon.global;

import java.util.Arrays;
import java.util.List;

/**
 * @Description:
 * @Author: ws
 * @Date: 2024/5/27 15:43
 */
public enum ErrCodeEnum {
    SUCCESS("200", "成功"),
    UNKNOWN("999", "服务器异常，请稍后再试"),
    ID_IS_NULL_ERROR("1000", "id不能为空"),
    SELECT_ERROR("990008", "查询失败"),
    NO_DATA("990009", "数据不存在"),

    KB_ID_PARAM_ERROR("1001", "知识库id不能空，且大于0"),

    DOC_ID_PARAM_ERROR("1001", "文档id不能空，且大于0"),


    //index服务异常码
    KB_NAME_SAME_ERROR("10000", "已存在同名知识库"),
    KB_NOT_EXISTS_ERROR("10001", "知识库不存在"),
    KB_FILE_NOT_EXISTS_ERROR("10002", "知识库文件不存在"),
    FILE_PARSE_ERROR("10003", "解析文件出现异常"),
    DELETE_INDEX_ERROR("10004", "删除索引失败"),
    DELETE_VECTOR_ERROR("10005", "删除向量数据失败"),
    FAQ_SAVE_ERROR("10006", "保存问答对失败"),
    FAQ_DELETE_ERROR("10007", "删除问答对失败"),
    FAQ_LIST_ERROR("10008", "问答列表查询失败"),


    KB_FILE_UN_PARSED_ERROR("10009", "知识库文件还未解析"),
    FAQ_EXTRACT_ERROR("10010", "FAQ抽取失败"),
    DOC_CHUNK_ERROR("10011", "获取文本块失败"),
    FAQ_SAVE_ES_ERROR("10012", "保持问答对失败(es)"),
    FAQ_UPDATE_ERROR("10013", "更新问答对失败"),
    FILE_NAME_SAME_ERROR("10014", "文件名重复"),
    FILE_LIST_EMPTY_ERROR("10015", "文件为空"),
    FAQ_NOT_EXIST_ERROR("10016", "faq不存在"),
    FAQ_NOT_ENABLED_ERROR("10017", "没有需要启用的faq数据"),
    FILE_REVISE_DATE_ERROR("10018", "获取文修订日期失败"),
    FILE_NO_PARSE("10019", "文件必须解析成功后才能设置修订时间"),
    COMPRESSED_FILE_TYPE_ERROR("10020", "只支持上传zip或tar格式的压缩文件"),
    URL_SAME_ERROR("10021", "url重复"),
    DOWNLOAD_FROM_URL_ERROR("10022", "从url获取文件失败"),
    FOLER_NAME_SAME_ERROR("10023", "同一层级下文件名不能重复"),
    FAQ_SIMILAR_QUESTION_NUMS("10024", "最多只能创建%s个相似问"),
    FAQ_POLISH_ERROR("10025", "调用faq润色接口失败"),
    FAQ_GEN_SIMILAR_QUESTION_ERROR("10026", "生成相似问出现异常"),
    UPLOAD_FILE_ERROR("10027", "上传文件时出现异常"),
    NOT_SELECT_FAQ_SIMILAR_QUESTION("10028", "没有选择相似问"),
    UPDATE_ES_ERROR("10029", "更新失败(es)"),
    FAQ_UPDATE_ES_ERROR("10030", "更新问答对失败(es)"),
    FILE_GREATER_THAN_ONE("10031", "至少选中两个文件"),
    FILE_MULTI_VERSION_PARSE_ERROR("10032", "文件多版本解析出现异常"),
    FILE_OR_GROUP_NOT_NULL("10033", "文件和文件集不能同时为空"),
    FOLDER_NOT_EXISTS_ERROR("10034", "文件夹不存在"),
    FAQ_PARAM_ERROR("10035", "faq参数有误"),
    UPDATE_MILVUS_ERROR("10036", "更新失败(milvus)"),
    CONF_CHUNKOVERLAP_CHUNKSIZE("10037", "分段重叠长度设置必须小于最大分段长度"),
    FILE_NAME_ILLEGAL("10038", "文件名不合法,请重新命名"),
    KB_NAME_ILLEGAL("10039", "知识库名不合法,请重新命名"),
    KB_NAME_EMPTY_ERROR("10040", "知识库名为空"),
    RETRY_ERROR("10041", "重试多次仍然失败"),
    KB_CONFIG_TYPE_ILLEGAL("10043", "知识库配置类型有误"),


    //label
    LABEL_EXISTS("10040", "标签已存在"),
    LABEL_EMPTY("10041", "标签为空"),
    BIZ_TYPE_NOT_EXIST("10042", "无法处理的bizType"),
    PY_ES_LABEL_ERROR("10043", "es更新标签失败"),
    PY_MILVUS_LABEL_ERROR("10044", "milvus更新标签失败"),
    PY_LABEL_ERROR("10045", "标签更新失败"),


    //minio
    BUCKET_NOT_EXISTS_ERROR("20000", "桶不存在"),
    READ_OBJECT_STREAM_ERROR("200001", "读取对象流失败"),
    LIST_FOLDER_ERROR("200003", "读取目录失败"),
    PUT_OBJECT_ERROR("200004", "上传文件失败"),
    CREATE_BUCKET_ERROR("200005", "创建桶失败"),
    ENAME_OBJECT_ERROR("20006", "重命名对象失败"),
    RENAME_OBJECT_ERROR("20007", "重命名对象失败"),
    REMOVE_OBJECT_ERROR("20008", "删除对象失败"),
    UPLOAD_FILE_EXISTS_ERROR("20009", "文件已存在"),
    FILE_FRAGMENT_INCOMPLETE("20011", "文件片段不完整"),

    //authorization
    VERIFY_CODE_ERROR("30000", "验证码错误！"),
    USER_NOT_EXISTS_ERROR("30001", "用户不存在"),
    INPUT_PASSWD_ERROR("30002", "密码错误，请重新输入密码！"),
    USER_DISABLED_ERROR("30003", "账户被禁用，无法登录，请联系管理员"),
    PASSWORD_ILLEGAL("30004", "密码长度至少8位并且必须包含大小写字母和数字"),
    OLD_PASSWD_WRONG_ERROR("30005", "输入的旧密码与数据库的密码不一致"),
    NEW_OLD_PASSWD_SAME_ERROR("30006", "输入的新密码与旧密码一样"),
    USER_NAME_EXISTING_ERROR("30008", "该用户名已存在"),
    ADD_NEW_USER_ERROR("30009", "新增用户失败"),
    PASSWORD_NOT_SAME("30010", "密码和确认密码不一致"),
    REGIST_USER_ERROR("30011", "注册用户失败"),
    RESET_PASSWORD_ERROR("30012", "重置用户密码失败"),
    LOGIN_EXPIRE("30013", "登录失效已过，请重新登录"),
    NO_ROLE_EEROR("30014", "没有分配任何角色"),
    HAS_NOT_LOGIN("30015", "尚未登录，请登录"),
    INSUFFICIENT_PERMISSIONS("30016", "没有足够权限"),
    RESOURCE_URL_REPEAT("30017", "url重复"),
    ROLE_NAME_REPEAT("30018", "已存在相同名的角色"),
    USER_EMPTY("30019", "用户为空"),
    NO_ROLE_ERROR("30020", "该用户未分配角色,请联系管理员"),
    UNAUTHORIZED("30021", "没有足够的权限"),
    NO_TOKEN("30022", "没有token"),
    TOKEN_NO_SAMEN("30023", "当前用户在其他地方登录"),
    ROLE_BINDING_USER("30024", "当前角色已关联用户"),
    GROUP_NAME_REPEAT("30025", "机构组名称已经存在"),
    GROUP_BINDING_USER("30026", "当前机构已关联用户"),
    GROUP_BINDING_DATA("30027", "当前机构已关联数据"),
    ROLE_ADMIN_NO_UPDATE("30028", "管理员角色不允许修改"),
    NO_GROUP_PERMISSION("30029", "没有机构组数据权限"),
    NO_USER_PERMISSION("30030", "没有用户数据权限"),
    USER_LOGIN_PARAM_ERROR("30031", "用户名或密码错误"),
    NOT_SUPPORT_REGISTER_USER("30032", "暂不支持用户注册"),
    USER_ADMIN_NO_UPDATE("30033", "管理员账号不能修改"),
    USER_PARAMETER_VERIFY_FAIL("30034", "用户参数校验失败"),
    USER_UPDATE_FAIL("30035", "用户更新失败"),
    NO_DEPT_PERMISSION("30036", "没有部门数据权限"),

    DEPARTMENT_ALREADY_EXIST("30036", "部门已存在"),

    DEPARTMENT_NON_EXIST("30037", "部门不存在"),

    DEPARTMENT_CREATE_ERROR("30038", "创建部门失败"),

    DEPARTMENT_EDIT_ERROR("30039", "编辑部门失败"),

    DEPARTMENT_QUERY_ERROR("30040", "查询部门失败"),

    DEPARTMENT_DELETE_ERROR("30041", "删除部门失败"),
    PARAM_LIST_EMPTY("30042", "参数列表为空"),

    PARAM_VALID_FAILURE("30043", "参数验证失败"),
    TIME_FORMAT_ERROR("30044", "起始日期或终止日期格式不正确"),

    USER_RESIGNED_ERROR("30045", "用户已离职，无法登录"),
    USER_PHONE_REPEAT("30046", "手机号已被使用"),
    USER_EMAIL_REPEAT("30047", "邮箱已被使用"),

    TRANSFER_PROPERTY_SAME_USER("30048", "资源转移人和接收人一致"),

    PARENT_DEPT_NOT_EXIST("30049", "上级部门不存在"),


    APP_KEY_NOT_EXIST("30050", "appKey不存在"),

    APP_KEY_NOT_NULL("30051", "appKey不能为空"),

    TRIAL_DATE_EXPIRED("30099", "产品试用已过期"),

    //qa异常码
    CONFIG_STATUS_ERROR("4000", "查询配置状态不合法"),
    DIALOG_NAME_SAME_ERROR("4001", "新名称不能与原对话名称相同"),
    DIALOG_RENAME_FAIL_ERROR("4002", "对话命名失败"),
    CONF_RELATION_USER_ERROR("4003", "该项配置已经关联用户！"),
    CONF_RELATION_ROLE_ERROR("4004", "该项配置已经关联角色！"),
    AI_FAIL_ERROR("4005", "ai算法服务器异常"),
    NO_SEARCH_CONFIG("4006", "未找到检索配置信息，请联系管理员"),

    NOT_AUDIO_EMPTY("4007", "删除语音不能为空"),

    SPEECH_RECOGNITION_ERROR("4008", "语音识别失败"),
    DIALOG_NOT_EXISTS_ERROR("4009", "对话不存在"),
    FAQ_SELECT_ERROR("4010", "faq筛选接口调用失败"),
    API_KEY_NOT_LEGAL("4011", "apiKey不合法"),
    RETRIEVE_DOC_ERROR("4012", "召回文档失败"),
    RETRIEVE_SQL_ERROR("4013", "调用sql生成失败"),

    //敏感词
    CONTAINS_SENS_WORD("5001", "存在敏感词"),
    WORDS_TOO_LONG("5002", "敏感词太长"),
    PARAM_IS_NULL("5003", "参数为空"),

    PARAM_ILLEGAL("5004", "参数非法"),

    //jodconverter libreoffice
    CONVERT_FILE_ERROR("6001", "源文件转换格式失败"),
    LIBREOFFICE_ERROR("6002", "libreoffice错误"),
    XWPFDOCUMENT_ERROR("6003", "XWPFDocument转化pdf失败"),

    // 模型
    MODEL_NAME_SAME_ERROR("7001", "已存在同名模型"),
    MODEL_IDE_SAME_ERROR("7002", "已存在该待接入模型"),
    MODEL_NOT_EXIST("7003", "模型不存在"),
    MODEL_IDE_IS_NULL("7004", "待接入的模型ID不能为空"),
    MODEL_TYPE_NOT_FOUND("7005", "暂不支持该模型类型"),
    MODEL_ID_FORMAT_ERROR("7006", "模型ID必须是正整数"),
    MODEL_NOT_AVAILABLE("7007", "模型不可用"),
    MODEL_CHECK_FAIL("7008", "远程调用检测模型可用性接口失败"),
    MODEL_TYPE_IS_NULL("7009", "模型类型不能为空"),
    MODEL_NAME_IS_NULL("7010", "模型名称不能为空"),

    //图实例查询域:21xxx
    EXECUTE_GRAPH_QUERY_ERROR("210001", "图谱实例查询失败"),
    NO_GRAPH_EDGE_ERROR("210002", "图谱边不存在"),
    DELETE_GRAPH_ERROR("210003", "删除图数据失败"),
    GRAPH_PARSE_ERROR("210004", "文件图解析失败"),


    //数据库域
    DB_NOT_EXISTS("31000", "数据库不存在"),
    DB_EXISTS("31001", "数据库已存在"),
    DATA_TABLE_EXCEL_MULTI_SHEET("31002", "文件表不支持多个sheet"),
    DATA_TABLE_FILE_NAME_EXISTS("31003", "追加文件和源文件名称重复"),
    APPEND_DATA_TABLE_FILE_NAME_EXISTS("31004", "追加文件与已有文件名称重复"),
    DB_TYPE_IS_NULL("31005", "数据库类型不能为空"),
    NAME_IS_NULL("31006", "名称不能为空"),
    DB_HOST_IS_NULL("31007", "连接地址不能为空"),
    DB_PORT_IS_NULL("31008", "连接端口不能为空"),
    DB_NAME_IS_NULL("31009", "数据库名称不能为空"),
    DB_USER_IS_NULL("31010", "连接用户不能为空"),
    DB_PASSWORD_IS_NULL("31011", "连接密码不能为空"),

    //文件解析回调函数异常码
    INTERIOR_ERROR("1101", "文件解析内部错误"),
    SERVER_ERROR("1200", "服务端错误"),
    FILE_TOO_MUCH_ERROR("1300", "文件数量超过限制"),
    MODEL_ERROR("1300", "解析模型异常，请重试，如重试后仍异常请联系管理员。"),
    MINERU_DOWN_ERROR("1301", "系统服务异常，请联系管理员。"),
    MINERU_MEMORY_ERROR("1302", "解析服务显存不足，请联系管理员处理。"),
    MODEL_TOKEN_ERROR("1303", "文档超长，请将文档拆分后重新上传。"),
    INDEX_SERVER_ERROR("1400", "index服务请求内部错误"),
    MILVUS_INSERT_ERROR("1401", "index milvus服务向量插入失败"),
    MILVUS_ERROR("1402", "index milvus服务插入向量维度不符合要求"),
    ES_ERROR("1403", "index es服务插入失败"),
    RE_EMBEDDING_ERROR("1404", "重新向量化失败"),
    RETRY_TIMES_EXCEEDED("1405", "超过最大重试次数"),
    TASK_REJECT("1406", "线程池满被拒绝执行"),
    MIGRATE_FAILED("1407","向量迁移失败");


    private String errCode;
    private String errMsg;

    public String getErrCode() {
        return errCode;
    }

    public String getErrMsg() {
        return errMsg;
    }

    ErrCodeEnum(String errCode, String errMsg) {
        this.errCode = errCode;
        this.errMsg = errMsg;
    }

    public static ErrCodeEnum getFileParseError(String errCode) {
        List<ErrCodeEnum> errCodeEnums = Arrays.asList(INTERIOR_ERROR, SERVER_ERROR, FILE_TOO_MUCH_ERROR, MODEL_ERROR, MINERU_DOWN_ERROR, MINERU_MEMORY_ERROR, MODEL_TOKEN_ERROR, INDEX_SERVER_ERROR, MILVUS_INSERT_ERROR, MILVUS_ERROR, ES_ERROR);
        for (ErrCodeEnum errCodeEnum : errCodeEnums) {
            if (errCodeEnum.getErrCode().equals(errCode))
                return errCodeEnum;
        }
        return null;
    }

    public ErrCodeEnum detail(String existedUsers) {
        this.errMsg = String.format(errMsg, existedUsers);
        return this;
    }
}
