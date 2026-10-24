package com.gientech.ragcommon.index.request;

import com.gientech.ragcommon.index.dto.KnowledgeBaseFileDTO;
import com.gientech.ragcommon.index.enmus.FileListTypeEnums;
import com.gientech.ragcommon.index.enmus.UploadFileTypeEnums;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.apache.commons.lang3.StringUtils;
import org.springframework.web.multipart.MultipartFile;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

@Schema(name = "文件批量上传请求参数", requiredProperties = {"kbId", "fileList"})
@Data
@AllArgsConstructor
@NoArgsConstructor
public class UploadFileListReq {

    @Schema(name = "kbId", description = "知识库id")
    @NotNull(message = "kbId不能为空")
    private Long kbId;

    @Schema(name = "PrimitiveName", description = "知识库名")
    private String primitiveName;

    @Schema(name = "fileListType", description = "列表类型: 1 文件解析列表；2 FAQ解析列表 3 图谱解析 4:文档上传问答 默认值 1")
    private Integer fileListType = FileListTypeEnums.FILE_LIST.getCode();

    @Schema(name = "isParse", description = "是否解析 默认false")
    private Boolean isParse = false;

    @Schema(name = "isExtract", description = "是否抽取 默认 false")
    private Boolean isExtract = false;

    @Schema(name = "isGraphParse", description = "是否图谱解析(图谱解析需要先对文档抽取,根据文本块进行图数据生成) 默认 false")
    private Boolean isGraphParse = false;

    @Schema(name = "fileList", description = "上传文件列表")
    private List<UploadFile> fileList;

    @Schema(name = "folderId", description = "上传文件基目录id：默认为null 知识库根目录")
    private Long folderId;

    private String platform = "rag-qa";

    /**
     * 默认做chunk化
     */
    private boolean chunking = true;

    @Schema(name = "saveTxt",description = "是否将解析结果的文字全文保存到minio的txt文件中'，default=False")
    private Boolean saveTxt = false;

    @Schema(name = "needChunk",description = "是否需要进行切分和索引’default=True)")
    private Boolean needChunk = true;


    public UploadFileListReq swallowCopy() {
        return new UploadFileListReq(kbId, primitiveName, fileListType, isParse, isExtract, isGraphParse, new ArrayList<>(), folderId, platform, chunking,saveTxt,needChunk);
    }

    @Data
    public static class UploadFile {

        @Schema(name = "multipartFile", description = "文件流")
        private MultipartFile multipartFile;

        @Schema(name = "fileName", description = "文件名称")
        private String fileName;

        @Schema(name = "type", description = "文件处理方式:SKIP:跳过;OVERWRITE:覆盖;NEWVERSION:新版本")
        private UploadFileTypeEnums type;

        @Schema(name = "compressedFileList", description = "待处理压缩文件列表")
        private List<CompressedUploadFile> compressedFileList;

        @Schema(name = "sourceUrl", description = "文件导入Url")
        private String sourceUrl;

        private boolean chunking;

        @Schema(name = "uid", description = "文件的uid(uid是前端生成的,文档上传问答使用,通过uid来判断文件解析状态)")
        private String uid;

        public String getFileName() {
            return StringUtils.isNotBlank(fileName) ? fileName.replace(" ","") : fileName;
        }

        @Data
        public static class CompressedUploadFile {
            @Schema(name = "filePath", description = "文件名称(包含压缩包里的路径)")
            private String filePath;

            @Schema(name = "type", description = "文件处理方式:SKIP:跳过;OVERWRITE:覆盖;NEWVERSION:新版本")
            private UploadFileTypeEnums type;
        }
    }


    public List<KnowledgeBaseFileDTO> getSimpleFileList() {
        List<KnowledgeBaseFileDTO> fileListWR = new ArrayList<>();
        AtomicInteger index = new AtomicInteger(0);
        this.fileList.forEach(file -> {
            KnowledgeBaseFileDTO fileWR = new KnowledgeBaseFileDTO();
            fileWR.setFileName(file.getFileName());
            Integer current = index.getAndIncrement();
            fileWR.setIndex(current);
            fileListWR.add(fileWR);
        });
        return fileListWR;
    }

}
