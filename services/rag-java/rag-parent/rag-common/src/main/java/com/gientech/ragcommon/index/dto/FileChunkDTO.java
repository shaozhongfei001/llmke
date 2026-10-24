package com.gientech.ragcommon.index.dto;

import com.alibaba.fastjson2.JSONArray;
import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.List;

/**
 * @Descrption:
 * @Author:liutaiyun
 * @Date:2024/08/19 15:58
 **/
@Schema(name = "文件chunk信息")
@Data
public class FileChunkDTO {

    /**
     * chunk的id
     */
    @JsonSerialize(using = ToStringSerializer.class)
    private Long id;

    /**
     * chunk内容
     */
    private String content;

    /**
     * 关联的图片的chunk的id集合
     */
//    @JsonSerialize(using = ToStringSerializer.class)
    private List<Long> picChunkIdList;

    /**
     * 关联的图片的URL
     */
    private List<String> picUrlList;

    /**
     * 图片url
     */
    private String imagePath;

    /**
     * 文本块位置 (四个点，左上为原点 顺时针)
     */
    private JSONArray positions;

    /**
     * 当前文本块所在原文的页数
     */
    private JSONArray pageNumbers;

    /**
     * pdf页面的宽和高(第一个是宽度,第二值是高度)
     */
    private JSONArray pageSizes;

    /**
     * offsets
     */
    private JSONArray offsets;

    /**
     * chunk类型  text image table
     */
    private String type;

    /**
     * 数据所在index的名称
     */
    private String tableName;

    /**
     * 数据所在的表明
     */
    private String table;
}
