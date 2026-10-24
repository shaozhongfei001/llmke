package com.gientech.ragcommon.index.dto;


import com.gientech.ragcommon.index.constant.IndexConstant;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import org.apache.commons.lang3.StringUtils;


@Schema(name = "文件信息")
@Data
public class FilePathDTO {

    @Schema(name = "name", description = "文件名称")
    private String name;

    @Schema(name = "uid",description = "文件的uid")
    private String uid;

    @Schema(name = "filePath", description = "源文件url")
    private String filePath;

    @Schema(name = "convertedFilePath", description = "解析后的url")
    private String convertedFilePath;

    @Schema(name = "size", description = "文件大小 M")
    private String size;

    @Schema(name = "txtFilePath",description = "文件解析后的结果")
    private String txtFilePath;

    @Schema(name = "pdfPages",description = "pdf页数")
    private Integer pdfPages;

//    @Schema(name = "type", description = "如果是图片的话,就是image,其他类型不用处理")
//    private String type;

    /**
     * 如果是图片的话,就是image,其他类型不用处理
     * @return
     */
    public String getType(){
        if(!StringUtils.isEmpty(name)){
            String fileType = name.substring(name.lastIndexOf(".") + 1);
            return IndexConstant.IMAGE_TYPE_LIST.contains(fileType) ? "image" : "file";
        }
        return "file";
    }
}
