package com.gientech.ragindexservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.plugins.pagination.PageDTO;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.gientech.ragcommon.auth.enums.BizTypeEnums;
import com.gientech.ragcommon.auth.enums.PrivilegeTypeEnums;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.CommonResponse;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.graph.dto.GraphInstanceDTO;
import com.gientech.ragcommon.index.constant.IndexConstant;
import com.gientech.ragcommon.index.dto.*;
import com.gientech.ragcommon.index.enmus.*;
import com.gientech.ragcommon.index.parameter.FileParseTaskInfo;
import com.gientech.ragcommon.index.request.*;
import com.gientech.ragcommon.index.utils.JSONPagination;
import com.gientech.ragcommon.infrastructure.emuns.MessageChannel;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragcommon.infrastructure.page.PageExt;
import com.gientech.ragcommon.infrastructure.utils.FileUtils;
import com.gientech.ragcommon.infrastructure.utils.PdfUtils;
import com.gientech.ragindexservice.application.remote.*;
import com.gientech.ragindexservice.application.service.FileAppService;
import com.gientech.ragindexservice.application.service.KnowledgeBaseListAppService;
import com.gientech.ragindexservice.application.service.ModelInfoAppService;
import com.gientech.ragindexservice.domain.entity.*;
import com.gientech.ragindexservice.domain.service.*;
import com.gientech.ragindexservice.infrastructure.RemoteFileUtils;
import com.gientech.ragindexservice.infrastructure.UrlKeywordChecker;
import com.gientech.ragindexservice.infrastructure.converter.KbFileExtConverter;
import com.gientech.ragindexservice.infrastructure.factory.FileProcessorContext;
import com.gientech.start.storage.exception.FileStorageException;
import com.gientech.start.storage.model.FileInfo;
import com.gientech.start.storage.properties.StorageProperties;
import com.gientech.start.storage.utils.FileStorageUtils;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import com.google.common.collect.Sets;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.compress.archivers.ArchiveEntry;
import org.apache.commons.compress.archivers.ArchiveInputStream;
import org.apache.commons.compress.archivers.ArchiveStreamFactory;
import org.apache.commons.io.FilenameUtils;
import org.apache.commons.io.IOUtils;
import org.apache.commons.lang3.ArrayUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.math.NumberUtils;
import org.apache.rocketmq.spring.core.RocketMQTemplate;
import org.apache.tika.Tika;
import org.jodconverter.core.DocumentConverter;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.Resource;
import org.springframework.core.io.UrlResource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.messaging.support.MessageBuilder;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.CollectionUtils;
import org.springframework.web.multipart.MultipartFile;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Function;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import static com.gientech.ragcommon.index.constant.IndexConstant.*;
import static com.gientech.ragcommon.index.constant.KbConfigConstant.*;

/**
 * <p>
 * 知识库明细 服务类
 * </p>
 *
 * @author wudf
 * @since 2024-06-04
 */
@Slf4j
@Service
public class KnowledgeBaseListAppServiceImpl implements KnowledgeBaseListAppService {

    @Autowired
    private KnowledgeBaseListDomainService knowledgeBaseListDomainService;

    @Autowired
    private KnowledgeBaseDomainService knowledgeBaseDomainService;

    @Autowired
    private SynLogDomainService synLogDomainService;

    @Autowired
    private FolderInfoDomainService folderInfoDomainService;

    @Autowired
    private RemoteFileUtils remoteFileUtils;

    @Autowired
    private ChunnkDomainService chunnkDomainService;

    @Autowired
    private GraphDomainService graphDomainService;

    @Autowired
    private RocketMQTemplate rocketMQTemplate;

    @Autowired
    private GraphSearchClient graphSearchClient;

    @Autowired
    private PrivilegeClient privilegeClient;

    @Autowired
    private FileAppService fileAppService;

    @Autowired
    private KbLabelHisDomainService kbLabelHisDomainService;

    @Autowired
    private BizLabelDomainService bizLabelDomainService;

    @Autowired
    private FileStorageUtils fileStorageUtils;

    @Autowired
    private StorageProperties storageProperties;

    @Autowired
    private DialoguaClient dialoguaClient;

    @Autowired
    private FolderInfoDomainService folderDomainService;

    @Autowired
    private ModelInfoAppService modelInfoAppService;

    @Autowired
    private DocumentConverter converter;

    @Autowired
    private FileProcessorContext fileProcessorContext;

    @Autowired
    private SearchConfigClient searchConfigClient;

    @Autowired
    private FileParseTaskDomainService fileParseTaskDomainService;

    @Value("${kb.file-parse.retry-limit:3}")
    private Integer retryLimit;
    @Autowired
    private PyMilvusClient pyMilvusClient;

    @Override
    public Page<KnowledgeBaseFileDTO> list(KnowledgeBaseFileQueryReq req) {
        Long kbId = req.getKbId();
        Integer basicPermission = knowledgeBaseDomainService.getHighestPermission(kbId);
        String parentFileName = req.getParentFileName();
        String fuzzy = req.getFuzzy();
        Integer status = req.getStatus();
        Integer faqExtractStatus = req.getFaqExtractStatus();
        Long pageNo = req.getPageNo();
        Long pageSize = req.getPageSize();
        Integer fileListType = req.getFileListType();
        Page<KnowledgeBaseList> knowledgeBasePage = knowledgeBaseListDomainService
                .list(kbId, fileListType, fuzzy, status, faqExtractStatus, parentFileName, pageNo, pageSize);
        Page<KnowledgeBaseFileDTO> result = new Page<>();
        BeanUtil.copyProperties(knowledgeBasePage, result);
        result.setRecords(BeanUtil.copyToList(knowledgeBasePage.getRecords(), KnowledgeBaseFileDTO.class));
        buildKbFileListResult(kbId, fileListType, result, basicPermission);
        return result;
    }

    @Override
    public Boolean deleteById(Long id) {
        KnowledgeBaseList knowledgeBaseFile = knowledgeBaseListDomainService.findById(id);
        Integer status = knowledgeBaseFile.getStatus();
        if (KbFileStatusEnums.NORMAL.getValue().equals(status) || KbFileStatusEnums.PARSE_SUCCESS.getValue().equals(status) || KbFileStatusEnums.PARSE_FAIL.getValue().equals(status)) {
            Long kbId = knowledgeBaseFile.getKbId();
            KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
            String primitiveName = knowledgeBase.getPrimitiveName();
            if (knowledgeBaseListDomainService.deleteById(id) > 0) {
                return deleteRemoveFile(knowledgeBaseFile, primitiveName, false);
            }
        }
        return false;
    }

    private Boolean deleteRemoveFile(KnowledgeBaseList knowledgeBaseFile, String primitiveName, Boolean isParse) {
        Integer parseType = knowledgeBaseFile.getParseType();
        String fileType = knowledgeBaseFile.getFileName().substring(knowledgeBaseFile.getFileName().lastIndexOf(".") + 1);
        Integer status = knowledgeBaseFile.getStatus();
        String filePath = knowledgeBaseFile.getConvertedFilePath();

        if (StringUtils.isNotBlank(filePath)) {
            if (FILE_TYPE_LIST.contains(fileType))
                filePath = knowledgeBaseFile.getFilePath();
            List<String> filePaths = Arrays.asList(filePath.replace(storageProperties.getDefaultStorageProperties().getEndPoint() + "/", ""));
            //删除文本块相关的数据
            if (
                    (Arrays.asList(KbFileStatusEnums.PARSE_SUCCESS.getValue(), KbFileStatusEnums.PARSE_FAIL.getValue()).contains(status) && (Arrays.asList(ParseTypeEnums.FILE_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode()).contains(parseType)))
                            || GraphParseStatusEnums.PARSE_SUCCESS.getValue().equals(knowledgeBaseFile.getGraphParseStatus())
            ) {
                //删除表
                chunnkDomainService.delFiles(primitiveName, filePaths);
                //删除table_summary_(摘要表)
                chunnkDomainService.delFiles(FileFieldEnums.TABLE_SUMMARY_PREFIX + primitiveName, filePaths);
                //删除 table_chunks_(chunk数据)
                chunnkDomainService.delFiles(FileFieldEnums.TABLE_CHUNKS_PREFIX + primitiveName, filePaths);
            }
        }

        //删除图相关的数据
        if (GraphParseStatusEnums.PARSE_SUCCESS.getValue().equals(knowledgeBaseFile.getGraphParseStatus())) {
            //删除图空间下某个文件对应的点和边的数据
            graphDomainService.delGraphSpace(primitiveName, knowledgeBaseFile.getId());
            //milvus中图实体表删除
            String fileName = filePath.substring(filePath.lastIndexOf("/") + 1);
            graphDomainService.delGraphEntity(primitiveName, Arrays.asList(String.valueOf(knowledgeBaseFile.getId())), Arrays.asList(fileName));
        }
        return true;
    }


    private FilesParseReq buildFilesParseParam(List<KnowledgeBaseFileDTO> kbFiles, Long kbId, String primitiveName, boolean chunking) {
        FilesParseReq filesParseReq = new FilesParseReq();
        if (CollectionUtils.isEmpty(kbFiles)) {
            return filesParseReq;
        }
        filesParseReq.setKnowledgeBaseId(kbId);
        filesParseReq.setKnowledgeBaseName(primitiveName);
        Map<String, String> idLabelMap = bizLabelDomainService.findLabelByFileIdsAndFolderIds(kbFiles.stream().map(KnowledgeBaseFileDTO::getId).toList(), List.of());

        List<FilesParseReq.File> files = kbFiles.stream().map(fileInfo -> {
            setFileLabel(idLabelMap, fileInfo);
            FilesParseReq.File file = new FilesParseReq.File();
            file.setFolderId(fileInfo.getFolderId());
            file.safeSetLabels(fileInfo.getLabel(), ",");
            file.setFileId(fileInfo.getId());
            file.setFileSize(fileInfo.getFileSize() + "MB");
            file.setParentFileName(fileInfo.getParentFileName());
            file.setFilePath(fileInfo.getFilePath());
            return file;

        }).collect(Collectors.toList());
        filesParseReq.setFiles(files);
        return filesParseReq;
    }


    @Override
    public KnowledgeBaseFileDTO uploadFile(Long kbId, Long fileId, String userId, MultipartFile file, List<MultipartFile> imagesFiles, List<MultipartFile> tableFiles, boolean isOverwrite) {

        KnowledgeBaseFileDTO knowledgeBaseFileDTO = new KnowledgeBaseFileDTO();
        KnowledgeBase dbKnowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(dbKnowledgeBase)) {
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        }
        KnowledgeBaseList sourceFile = knowledgeBaseListDomainService.findById(fileId);
        if (Objects.isNull(sourceFile)) {
            throw new ApplicationException(ErrCodeEnum.KB_FILE_NOT_EXISTS_ERROR);
        }
        dbKnowledgeBase.setId(null);

        String filePath = sourceFile.getFilePath();
        String objectName = filePath.replace(storageProperties.getDefaultStorageProperties().getDomain(), "");
        String folder = objectName.substring(0, objectName.lastIndexOf("/") + 1) + "parsed/";

        //String folder = getFolder(dbKnowledgeBase.getPlatform(), userId, dbKnowledgeBase.getPrimitiveName(), sourceFile.getParentFileName(), sourceFile.getVersion()) + "parsed/";
        log.info("folder path: {}", folder);

        try {
            //上传解析后的文件(文本块)
            if (!Objects.isNull(file) && !isEmptyFileStream(file)) {
                String originalFilename = file.getOriginalFilename();
                if (StringUtils.isNotBlank(originalFilename)) {
                    originalFilename = originalFilename.substring(0, originalFilename.lastIndexOf(".md"));
                    String fileType = originalFilename.substring(originalFilename.lastIndexOf(".") + 1);
                    if (TEXT_TYPE_LIST.contains(fileType)) {
                        log.info("file：{},---file.getOriginalFilename():{}", originalFilename, file.getOriginalFilename());
                        try {
                            MultipartFile newFile = new MockMultipartFile(
                                    file.getName(),                  // 表单字段名（保持原值）
                                    file.getOriginalFilename(),      // 原始文件名
                                    getContentType(file.getOriginalFilename()),                     // 显式设置 ContentType
                                    file.getBytes()                  // 文件内容
                            );
                            FileInfo fileInfo = fileStorageUtils.putObject(folder, newFile, null);
                            sourceFile.setParsedFilePath(fileInfo.getFilePath());
                            sourceFile.setConvertedFilePath(sourceFile.getParsedFilePath());
                        } catch (Exception e) {
                            log.error("MultipartFile:set contentType file");
                        }
                    }
                }
            }
            //上传图片(图片的chunk)
            if (!CollectionUtils.isEmpty(imagesFiles)) {
                imagesFiles = imagesFiles.stream().filter(multipartFile -> !isEmptyFileStream(multipartFile)).toList();
                log.info("imagesFiles:{}--start", imagesFiles.size());
                List<MultipartFile> filesWithType = new ArrayList<>();
                for (MultipartFile itemFile : imagesFiles) {
                    try {
                        if (Objects.isNull(itemFile.getContentType())) {
                            MultipartFile newFile = new MockMultipartFile(
                                    itemFile.getName(),                  // 表单字段名（保持原值）
                                    itemFile.getOriginalFilename(),      // 原始文件名
                                    getContentType(itemFile.getOriginalFilename()),                     // 显式设置 ContentType
                                    itemFile.getBytes()                  // 文件内容
                            );
                            filesWithType.add(newFile);
                        } else {
                            filesWithType.add(itemFile);
                        }
                    } catch (Exception e) {
                        log.error("MultipartFile:set contentType imagesFiles");
                    }
                }
                if (!CollectionUtils.isEmpty(filesWithType)) {
                    String imageFolder = folder + "images/";
                    log.info("imageFolder:{}", imageFolder);
                    List<FileInfo> imageFileInfos = fileStorageUtils.putObjects(imageFolder, filesWithType.toArray(new MultipartFile[filesWithType.size()]), null);
                    knowledgeBaseFileDTO.setImagePaths(imageFileInfos
                            .stream().map(FileInfo::getFilePath).toList());
                    sourceFile.setImagePaths(knowledgeBaseFileDTO.getImagePaths());

                }
            }

            if (!CollectionUtils.isEmpty(tableFiles)) {
                tableFiles = tableFiles.stream().filter(multipartFile -> !isEmptyFileStream(multipartFile)).toList();
                List<MultipartFile> filesWithType = new ArrayList<>();
                for (MultipartFile itemFile : tableFiles) {
                    try {
                        if (Objects.isNull(itemFile.getContentType())) {
                            MultipartFile newFile = new MockMultipartFile(
                                    itemFile.getName(),                  // 表单字段名（保持原值）
                                    itemFile.getOriginalFilename(),      // 原始文件名
                                    getContentType(itemFile.getOriginalFilename()),                     // 显式设置 ContentType
                                    itemFile.getBytes()                  // 文件内容
                            );
                            filesWithType.add(newFile);
                        } else {
                            filesWithType.add(itemFile);
                        }
                    } catch (Exception e) {
                        log.error("MultipartFile:set contentType tableFiles");
                    }
                }
                if (!CollectionUtils.isEmpty(filesWithType)) {
                    String tableFolder = folder + "tables/";
                    log.info("tables:{}", tableFolder);
                    List<FileInfo> tableFileInfos = fileStorageUtils.putObjects(tableFolder, filesWithType.toArray(new MultipartFile[filesWithType.size()]), null);
                    List<String> tableFilePaths = tableFileInfos
                            .stream().map(FileInfo::getFilePath).toList();
                    knowledgeBaseFileDTO.setTableFilePaths(JSON.toJSONString(tableFilePaths));
                    sourceFile.setTableFilePaths(knowledgeBaseFileDTO.getTableFilePaths());
                }
            }
            knowledgeBaseListDomainService.update(sourceFile);
        } catch (FileStorageException ex) {
            log.error(ex.getMessage(), ex);
            throw new ApplicationException(ErrCodeEnum.PUT_OBJECT_ERROR);
        }
        BeanUtil.copyProperties(sourceFile, knowledgeBaseFileDTO);
        return knowledgeBaseFileDTO;
    }


    public String getContentType(String filename) {
        String extension = FilenameUtils.getExtension(filename);
        log.info("filename:{},--extension:{}", filename, extension);
        if (extension == null) return "application/octet-stream"; // 默认类型
        return switch (extension.toLowerCase()) {
            // 主流图片格式
            case "jpg", "jpeg" -> "image/jpeg";      // JPEG格式[1,6,8](@ref)
            case "png" -> "image/png";               // PNG格式[1,6,8](@ref)
            case "gif" -> "image/gif";               // GIF动图[1,6,8](@ref)
            case "webp" -> "image/webp";             // WebP高效图片[1,6,8](@ref)
            case "svg" -> "image/svg+xml";           // SVG矢量图[1,6,8](@ref)
            // 扩展更多类型...
            case "md" -> "text/markdown";
            default -> "application/octet-stream";
        };
    }

    boolean isEmptyFileStream(MultipartFile multipartFile) {
        try {
            if (Objects.isNull(multipartFile) || multipartFile.getSize() == 0 || multipartFile.getBytes().length == 0 || multipartFile.isEmpty())
                return true;
            InputStream inputStream = multipartFile.getInputStream();
            return !(inputStream.available() > 0 || inputStream.read() != -1);
        } catch (IOException ex) {
            log.error(ex.getMessage(), ex);
            throw new ApplicationException(ErrCodeEnum.PUT_OBJECT_ERROR);
        }
    }

    @Transactional
    public List<KnowledgeBaseFileDTO> addKnowledgeBaseList(Long kbId, String rootSourceUrl, List<KbFile> kbFiles, Integer parseType, List<Integer> parseTypes, boolean chunking) {
        List<KnowledgeBaseList> dbKbFiles = knowledgeBaseListDomainService.findFileByKbId(kbId, parseTypes);
        Map<String, KnowledgeBaseList> dbFileMap = Maps.newHashMap();
        if (!CollectionUtils.isEmpty(dbKbFiles)) {
            dbKbFiles.forEach(dbFile -> dbFileMap.put(dbFile.getFileName(), dbFile));
        }
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase)) {
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        }
        List<KnowledgeBaseList> knowledgeBaseListsResult = Lists.newArrayList();
        List<KnowledgeBaseList> knowledgeBaseLists = Lists.newArrayList();
        List<Long> deleteFileIds = Lists.newArrayList();
        for (KbFile fileInfo : kbFiles) {
            KnowledgeBaseList knowledgeBaseList = new KnowledgeBaseList();
            knowledgeBaseList.setIsEnable(KbFileEnableEnums.ENABLE.getCode());
            knowledgeBaseList.setKbId(kbId);
            knowledgeBaseList.setChunking(chunking);
            knowledgeBaseList.setVersion(fileInfo.getVersion());
            knowledgeBaseList.setParseType(parseType);
            knowledgeBaseList.setParentFileName(fileInfo.getParentFileName());
            knowledgeBaseList.setGroupId(fileInfo.getGroupId());
            knowledgeBaseList.setFileName(fileInfo.getFileName());
            knowledgeBaseList.setFileSize(fileInfo.getFileSize());
            knowledgeBaseList.setFolderId(fileInfo.getFolderId());
            knowledgeBaseList.setSourceUrl(rootSourceUrl);
            knowledgeBaseList.setFilePath(rootSourceUrl + fileInfo.getObjectName());
            knowledgeBaseList.setChunking(fileInfo.isChunking());
            knowledgeBaseList.setUid(fileInfo.getUid());
            knowledgeBaseList.setTempStatus(ParseTypeEnums.DOC_QA.getCode().equals(parseType) ? TempStatusEnums.TEMP.getCode() : TempStatusEnums.PERSISTENCE.getCode());
            //如果文档上传问答&&文件类型是图片的话，不需要解析
//            if (ParseTypeEnums.DOC_QA.getCode().equals(parseType) && IndexConstant.IMAGE_TYPE_LIST.contains(fileName.substring(fileName.lastIndexOf(".") + 1))) {
//                knowledgeBaseList.setStatus(KbFileStatusEnums.PARSE_SUCCESS.getValue());
//            }
            knowledgeBaseLists.add(knowledgeBaseList);
            KnowledgeBaseList dbFile = dbFileMap.get(knowledgeBaseList.getFileName());
            if (!Objects.isNull(dbFile))
                deleteFileIds.add(dbFile.getId());
        }
        //删除
        if (!CollectionUtils.isEmpty(deleteFileIds))
            this.deleteByIds(deleteFileIds);
        //新增
        if (!CollectionUtils.isEmpty(knowledgeBaseLists))
            knowledgeBaseListsResult.addAll(knowledgeBaseListDomainService.insertBatch(knowledgeBaseLists));

        for (KnowledgeBaseList knowledgeBaseList : knowledgeBaseListsResult) {
            List<BizLabel> superiorLabels = findSuperiorLabel(knowledgeBaseList.getId(), knowledgeBaseList.getFolderId(), getBizTypeByParseType(parseType));
            bizLabelDomainService.saveBatch(superiorLabels);
        }
        return BeanUtil.copyToList(knowledgeBaseListsResult, KnowledgeBaseFileDTO.class);
    }

    private BizTypeEnums getBizTypeByParseType(Integer parseType) {
        if (parseType.equals(ParseTypeEnums.FAQ_MANAGEMENT.getCode())) {
            return BizTypeEnums.FAQ_FILE;
        }
        if (parseType.equals(ParseTypeEnums.FAQ_FILE_PARSE.getCode())) {
            return BizTypeEnums.FAQ_EXTRACT_FILE;
        }
        return BizTypeEnums.KNOWLEDGE_BASE_FILE;
    }

    @Override
    public Boolean filesParseNew(FilesParseReq filesParseReq) {
        Long kbId = filesParseReq.getKnowledgeBaseId();
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        //默认需要鉴权

        String config = knowledgeBase.getConfig();
        checkModel(config, filesParseReq.getNeedAuth(), filesParseReq);

        filesParseReq.adjustByPlatform(knowledgeBase.getPlatform());
        //解析所有
        if (filesParseReq.getIsAll()) {
            getFilePathByKbId(filesParseReq, Arrays.asList(ParseTypeEnums.FILE_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode()), Arrays.asList(KbFileStatusEnums.NORMAL.getValue(), KbFileStatusEnums.PARSE_SUCCESS.getValue(), KbFileStatusEnums.PARSE_FAIL.getValue()), null);
        } else {
            getFilePathByFolder(filesParseReq, Arrays.asList(KbFileStatusEnums.NORMAL.getValue(), KbFileStatusEnums.PARSE_SUCCESS.getValue(), KbFileStatusEnums.PARSE_FAIL.getValue()), null, null);
        }

        //文件多版本识别
        //默认需要多版本

        fileAppService.fileMultiversionParse(kbId, filesParseReq.getFiles().stream().map(FilesParseReq.File::getFileId).collect(Collectors.toList()), MultiversionParseEnums.FILENAME, Arrays.asList(ParseTypeEnums.FILE_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode()), filesParseReq.getNeedAuth());


        List<Long> fileIds = filesParseReq.getFiles().stream().map(FilesParseReq.File::getFileId).toList();
        List<Long> folderIds = filesParseReq.getFiles().stream().map(FilesParseReq.File::getFolderId).filter(Objects::nonNull).toList();
        Map<String, String> idLabelMap = bizLabelDomainService.findLabelByFileIdsAndFolderIds(fileIds, folderIds);

        //解析任务
        List<FileParseTask> taskList = Lists.newArrayList();
        //解析文件id
        List<Long> parseFileIds = Lists.newArrayList();
        filesParseReq.getFiles().forEach(file -> {
            //重新解析需要删除之前的数据
            KnowledgeBaseList kbFile = knowledgeBaseListDomainService.findById(file.getFileId());
            setFileLabel(idLabelMap, kbFile);
            if (filesParseReq.getReParse()) {
                deleteRemoveFile(kbFile, knowledgeBase.getPrimitiveName(), true);
            }
            file.setLabels(FilesParseReq.safeSetLabels(kbFile.getLabel(), ","));
            parseFileIds.add(file.getFileId());

            User user = UserContext.getUser();
            String userName = user.getUserName();
            String userId = user.getUserId();
            if (StringUtils.isBlank(userName) && StringUtils.isBlank(userId)) {
                userName = filesParseReq.getInnerCallUser();
                userId = filesParseReq.getInnerCallUserId();
            }

            //文件解析任务
            FileParseTaskInfo taskInfo = BeanUtil.copyProperties(filesParseReq, FileParseTaskInfo.class);
            taskInfo.setFiles(Collections.singletonList(BeanUtil.copyProperties(file, FileParseTaskInfo.File.class)));
            taskInfo.setIsExtract(false);
            taskInfo.setUserName(userName);
            taskInfo.setParseType(kbFile.getParseType());
            taskInfo.setNeedChunk(filesParseReq.isNeedChunk());
            taskInfo.setUserId(userId);
            taskInfo.setPrimitiveName(knowledgeBase.getPrimitiveName());
            taskInfo.setIndexName(knowledgeBase.getPrimitiveName());
            taskInfo.buildKbConf(knowledgeBase.getConfig());
            taskInfo.setNeedAuth(filesParseReq.getNeedAuth());


            //解析任务
            FileParseTask fileParseTask = new FileParseTask();
            fileParseTask.setKbId(knowledgeBase.getId());
            fileParseTask.setKbName(knowledgeBase.getPrimitiveName());
            fileParseTask.setFileId(file.getFileId());
            fileParseTask.setFileName(file.getFileName());
            fileParseTask.setTaskInfo(JSON.toJSONString(taskInfo));
            fileParseTask.setStatus(ParseTaskStatusEnums.PENDING.getCode());
            fileParseTask.setRetryLimit(retryLimit);
            fileParseTask.setRetryTimes(0);
            fileParseTask.setCreateBy(userName);
            fileParseTask.setModifyBy(userName);
            fileParseTask.setGmtCreate(new Date());
            // fileParseTask.setStartTime(fileParseTask.getGmtCreate());
            fileParseTask.setGmtModified(fileParseTask.getGmtCreate());
            taskList.add(fileParseTask);
//            rocketMQTemplate.syncSendOrderly(MessageChannel.KB_FILE_PARSE_EXTRACT_TOPIC, MessageBuilder.withPayload(taskInfo).build(),MessageChannel.KB_FILE_PARSE_EXTRACT_QUEUE);
//            rocketMQTemplate.syncSend(MessageChannel.KB_FILE_PARSE_EXTRACT_TOPIC, MessageBuilder.withPayload(fileParseMessage).build());
        });

        //更新状态
        knowledgeBaseListDomainService.updateParseStatusByIds(parseFileIds, KbFileStatusEnums.PARSE_WAIT.getValue(), true);
        //插入任务
        fileParseTaskDomainService.saveBatch(taskList);
        return true;
    }

    private void checkModel(String config, boolean needAuth, FilesParseReq filesParseReq) {
        if (StringUtils.isEmpty(config))
            return;
        JSONObject confJson = JSON.parseObject(config);
        String modelName = confJson.getString(MODEL_NAME);
        verifyModel(modelName, needAuth);
        String embeddingModelName = confJson.getString(EMBEDDING_MODEL_NAME);
        verifyModel(embeddingModelName, needAuth);
        filesParseReq.setEmbeddingModelName(embeddingModelName);
        String multiModelName = confJson.getString(MULTI_MODEL_NAME);
        verifyModel(multiModelName, needAuth);
        String faqModelName = confJson.getString(FAQ_MODEL_NAME);
        verifyModel(faqModelName, needAuth);
        String generateGraphModelName = confJson.getString(GENERATE_GRAPH_MODEL_NAME);
        verifyModel(generateGraphModelName, needAuth);

    }

    private void verifyModel(String modelName, boolean needAuth) {
        ModelSimpDTO modelInfo = modelInfoAppService.getByModeName(modelName, needAuth);
        if (Objects.isNull(modelInfo))
            throw new ApplicationException(ErrCodeEnum.MODEL_NOT_EXIST.getErrCode(), "您没有权限使用【" + modelName + "】模型，请联系管理员！");
    }

    private void getFilePathByKbId(FilesParseReq filesParseReq, List<Integer> parseTypes, List<Integer> parseStatus, List<Integer> faqExtractStatus) {
        List<FilesParseReq.File> files = filesParseReq.getFiles();
        Long KbId = filesParseReq.getKnowledgeBaseId();
        List<Long> excludeFolderIds = filesParseReq.getExcludeFolderIds();
        List<Long> excludeFileIds = filesParseReq.getExcludeFileIds();
        List<Long> resultFolderIds = Lists.newArrayList();

        if (!CollectionUtils.isEmpty(excludeFolderIds)) {
            resultFolderIds.addAll(excludeFolderIds);
            folderInfoDomainService.getChildrenFolderIds(excludeFolderIds, resultFolderIds);  //递归获取文件夹id
        }
        List<KnowledgeBaseList> kbFiles = knowledgeBaseListDomainService.findByKbId(KbId, parseTypes, resultFolderIds, excludeFileIds, parseStatus, faqExtractStatus);
        if (!CollectionUtils.isEmpty(kbFiles)) {
            kbFiles.forEach(kbFile -> {
                String convertedFilePath = kbFile.getConvertedFilePath();

                FilesParseReq.File file = new FilesParseReq.File();
                file.setFileId(kbFile.getId());
                if (StringUtils.isNotEmpty(convertedFilePath)) {
                    file.setFilePath(convertedFilePath.replace(storageProperties.getDefaultStorageProperties().getEndPoint() + "/", ""));
                }
                file.setFileSize(kbFile.getFileSize() + "MB");
                file.setParentFileName(kbFile.getParentFileName());
                files.add(file);

            });
        }
    }

    private void getFilePathByFolder(FilesParseReq filesParseReq, List<Integer> parseStatus, List<Integer> faqExtractStatus, List<Integer> graphParseStatus) {
        List<FilesParseReq.File> files = filesParseReq.getFiles();
        List<Long> resultFolderIds = filesParseReq.getFolderIds();
        if (!CollectionUtils.isEmpty(filesParseReq.getFolderIds())) {
            List<Long> folderIds = Lists.newArrayList(filesParseReq.getFolderIds());
            folderInfoDomainService.getChildrenFolderIds(folderIds, resultFolderIds);
        }
        List<KnowledgeBaseList> kbFiles = knowledgeBaseListDomainService.findByFolderIds(resultFolderIds, parseStatus, faqExtractStatus, graphParseStatus);
        if (!CollectionUtils.isEmpty(kbFiles)) {
            kbFiles.forEach(kbFile -> {
                String filePath = kbFile.getFilePath();
                FilesParseReq.File file = new FilesParseReq.File();
                file.setFileId(kbFile.getId());
                file.setFileName(kbFile.getFileName());
                file.setFilePath(filePath.replace(storageProperties.getDefaultStorageProperties().getEndPoint() + "/", ""));
                file.setFileSize(kbFile.getFileSize() + "MB");
                file.setParentFileName(kbFile.getParentFileName());
                files.add(file);
            });
        }
    }

    @Override
    public Boolean filesExtractFAQNew(FilesParseReq filesParseReq) {
        return doExtractFQA(filesParseReq, false);
    }

    @Override
    public Integer checkCunkFile(Long kbId, String fileName, String fileMd5) {
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase)) {
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        }
        KnowledgeBaseList knowledgeBaseFile = knowledgeBaseListDomainService.findFileByKbIdAndFileName(kbId, fileName);
        // 秒传
        String folder = knowledgeBase.getPrimitiveName() + "/";

        try {
            if (Objects.nonNull(knowledgeBaseFile) && fileStorageUtils.isExistedFile(folder, fileName, null)) {
                //文件已存在，下标为-2
                return -2;
            }
            // 读取目录里的所有文件
            List<FileInfo> fileInfos = fileStorageUtils.listFolderFiles(FILE_FRAGMENT_DIR + "/" + fileMd5, null);
            if (Objects.isNull(knowledgeBaseFile) && CollectionUtils.isEmpty(fileInfos)) {
                //文件没有上传过，下标为-1
                return -1;
            } else {
                //文件上传中断过，返回当前已经上传到的下标
                return fileInfos.size() - 1;
            }
        } catch (FileStorageException ex) {
            log.error(ex.getMessage(), ex);
            throw new ApplicationException(ErrCodeEnum.LIST_FOLDER_ERROR);
        }
    }

    @Override
    public Boolean chunkUpload(String fileMd5, MultipartFile file) {
        // 文件每次分片的下标
        String folder = FILE_FRAGMENT_DIR + "/" + fileMd5 + "/";
        try {
            fileStorageUtils.putObject(folder, file, null);
        } catch (Exception ex) {
            log.error(ex.getMessage(), ex);
            throw new ApplicationException(ErrCodeEnum.PUT_OBJECT_ERROR);
        }
        return true;
    }

    @Override
    public Boolean chunkMerge(FileMergeReq fileMergeReq) {
//        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(fileMergeReq.getKbId());
//        String folder = "/" + FILE_FRAGMENT_DIR + "/" + fileMergeReq.getFileMd5() + "/";
//        String fileName = fileMergeReq.getFileName();
//        Integer chunks = fileMergeReq.getChunks();
//
//        // 获取父文件名和版本号
//        String parentFileName = knowledgeBaseListDomainService.getParentFileName(fileName);
//        String version = knowledgeBaseListDomainService.getVersionByParentFileName(fileMergeReq.getKbId(), parentFileName);
//
//        // 本知识库下文件存放位置
//        String storedFilePathInKb = knowledgeBase.getKbName() + "_" + parentFileName + "/" + version + "/" + fileName;
//        String outputFile = knowledgeBase.getKbName() + "/" + storedFilePathInKb;
//
//        try {
//            FileInfo fileInfo = minioUtils.composeFileFragment(minioConfig.getDataBucketName(), outputFile, chunks, folder);
//            if (!Objects.isNull(fileInfo)) {
//                //删除文件片段
//                minioUtils.deleteAllFilesInFolder(minioConfig.getDataBucketName(), folder);
//            }
//            //将url保存到数据库
//            List<FileInfo> fileInfoList = new ArrayList<>(1);
//            fileInfoList.add(fileInfo);
//
//            List<KbFile> kbFiles = BeanUtil.copyToList(fileInfoList, KbFile.class);
//            KbFile kbFile = kbFiles.get(0);
//            kbFile.setParentFileName(parentFileName);
//            kbFile.setVersion(version);
//            // todo: 非pdf文件转化成pdf文件
//            kbFile.setObjectName(storedFilePathInKb);
//            kbFile.setConvertedObjectName();
//            addKnowledgeBaseList(fileMergeReq.getKbId(), knowledgeBase.getSourceUrl(), kbFiles, ParseTypeEnums.FILE_PARSE.getCode());
//            return true;
//        } catch (Exception ex) {
//            log.error(ex.getMessage(), ex);
//            throw new ApplicationException(ErrCodeEnum.PUT_OBJECT_ERROR);
//        }
        return true;
    }

    @Override
    public Boolean updateEnable(FileEnableReq fileEnableReq) {
        Integer enableStatus = fileEnableReq.getEnableStatus();
        List<Long> fileIds = fileEnableReq.getFileIds();
        return knowledgeBaseListDomainService.updateEnable(fileIds, enableStatus);
    }

    @Override
    public Integer getFileStatusById(Long fileId) {
        if (Objects.isNull(fileId)) {
            return null;
        }
        KnowledgeBaseList knowledgeBaseFile = knowledgeBaseListDomainService.findById(fileId);
        return Objects.isNull(knowledgeBaseFile) ? null : knowledgeBaseFile.getStatus();
    }

    @Override
    public KnowledgeBaseFileDTO getById(Long id) {
        if (Objects.isNull(id)) {
            return null;
        }
        KnowledgeBaseList knowledgeBaseFile = knowledgeBaseListDomainService.findById(id);
        KnowledgeBaseFileDTO fileDTO = Objects.isNull(knowledgeBaseFile) ? null : BeanUtil.copyProperties(knowledgeBaseFile, KnowledgeBaseFileDTO.class);
        if (!Objects.isNull(fileDTO)) {
            Long kbId = knowledgeBaseFile.getKbId();
            Integer basicPermission = knowledgeBaseDomainService.getHighestPermission(kbId);
            fileDTO.setPermission(basicPermission);
            fileDTO.setPdfPage(PdfUtils.getPdfPages(fileDTO.getConvertedFilePath()));
            setFilesPermission(kbId, basicPermission, List.of(fileDTO), BizTypeEnums.KNOWLEDGE_BASE_FILE.getCode());
        }
        return fileDTO;
    }

    @Override
    public List<KnowledgeBaseFileDTO> getByIds(Long[] ids) {
        if (ArrayUtils.isEmpty(ids)) {
            return Lists.newArrayList();
        }
        List<KnowledgeBaseList> knowledgeBaseFileList = knowledgeBaseListDomainService.findByIds(ids);
        return CollectionUtils.isEmpty(knowledgeBaseFileList) ? Lists.newArrayList() : BeanUtil.copyToList(knowledgeBaseFileList, KnowledgeBaseFileDTO.class);
    }

    @Override
    public List<FileChunkDTO> getFileChunks(Long docId, Integer pageNo, Integer pageSize) {
        return knowledgeBaseListDomainService.getFileChunks(docId, pageNo, pageSize);
    }

    @Override
    public List<FileMetadataChunkDTO> getFileMetadataChunks(Long docId, Integer pageNo, Integer pageSize) {
        return knowledgeBaseListDomainService.getFileMetadataChunks(docId, pageNo, pageSize);
    }

    @Override
    public void updateParseStatusByIds(List<Long> fileIds, Integer status, Boolean needUpdateTime) {
        knowledgeBaseListDomainService.updateParseStatusByIds(fileIds, status, needUpdateTime);
    }

    @Override
    public Integer getFileChunkCount(Long docId) {
        JSONObject respJson = knowledgeBaseListDomainService.getChunks(docId, 1, 1);
        if (Objects.isNull(respJson))
            return 0;
        JSONObject data = respJson.getJSONObject("data");
        if (Objects.isNull(data))
            return 0;
        Integer totalCount = data.getInteger("total_count");
        if (totalCount == null || Objects.isNull(totalCount))
            return 0;
        return totalCount;
    }


    @Override
    public List<FileChunkDTO> getFileChunks(Long kbId, Long docId) throws ApplicationException {
        if (Objects.isNull(kbId) || kbId < 0) {
            throw new ApplicationException(ErrCodeEnum.KB_ID_PARAM_ERROR);
        }
        if (Objects.isNull(docId) || docId < 0) {
            throw new ApplicationException(ErrCodeEnum.DOC_ID_PARAM_ERROR);
        }
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase)) {
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        }
        KnowledgeBaseList knowledgeBaseList = knowledgeBaseListDomainService.findById(docId);
        if (Objects.isNull(knowledgeBaseList)) {
            throw new ApplicationException(ErrCodeEnum.KB_FILE_NOT_EXISTS_ERROR);
        }
        if (knowledgeBaseList.getStatus() != KbFileStatusEnums.PARSE_SUCCESS.getValue()) {
            throw new ApplicationException(ErrCodeEnum.KB_FILE_UN_PARSED_ERROR);
        }

        return getFileChunks(docId, null, null);
    }

    @Override
    public Page<FileChunkDTO> getFileChunksByPage(Long kbId, Long docId, Integer pageNo, Integer pageSize) throws ApplicationException {
        Integer chunkCount = getFileChunkCount(docId);
        List<FileChunkDTO> chunks;
        if (Objects.isNull(kbId) || kbId < 0) {
            throw new ApplicationException(ErrCodeEnum.KB_ID_PARAM_ERROR);
        }
        if (Objects.isNull(docId) || docId < 0) {
            throw new ApplicationException(ErrCodeEnum.DOC_ID_PARAM_ERROR);
        }
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase)) {
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        }
        KnowledgeBaseList knowledgeBaseList = knowledgeBaseListDomainService.findById(docId);
        if (Objects.isNull(knowledgeBaseList)) {
            throw new ApplicationException(ErrCodeEnum.KB_FILE_NOT_EXISTS_ERROR);
        }
        if (knowledgeBaseList.getStatus() != KbFileStatusEnums.PARSE_SUCCESS.getValue()) {
            throw new ApplicationException(ErrCodeEnum.KB_FILE_UN_PARSED_ERROR);
        }
        chunks = getFileChunks(docId, pageNo, pageSize);
        PageExt<FileChunkDTO> page = new PageExt();
        page.setSize(pageSize);
        page.setCurrent(pageNo);
        page.setTotal(chunkCount);
        page.setRecords(chunks);
        page.setPdfPages(PdfUtils.getPdfPages(knowledgeBaseList.getConvertedFilePath()));
        return page;
    }

    @Override
    public Integer getFAQExtractStatusById(Long fileId) {
        if (Objects.isNull(fileId)) {
            return null;
        }
        KnowledgeBaseList knowledgeBaseFile = knowledgeBaseListDomainService.findById(fileId);
        return Objects.isNull(knowledgeBaseFile) ? null : knowledgeBaseFile.getFaqExtractStatus();
    }

    @Override
    public Boolean deleteByIds(List<Long> fileIds) {
        KnowledgeBaseList knowledgeBaseFile = knowledgeBaseListDomainService.findById(fileIds.get(0));
        List<KnowledgeBaseList> kbFiles = knowledgeBaseListDomainService.findByIds(fileIds);
        if (Objects.isNull(knowledgeBaseFile))
            throw new ApplicationException(ErrCodeEnum.KB_FILE_NOT_EXISTS_ERROR);
        Long kbId = knowledgeBaseFile.getKbId();
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        if (knowledgeBaseListDomainService.deleteByIds(fileIds)) {
            String primitiveName = knowledgeBase.getPrimitiveName();
            List<String> filePaths = Lists.newArrayList();
            kbFiles.forEach(file -> {
                Integer status = file.getStatus();
                if (KbFileStatusEnums.PARSE_SUCCESS.getValue().equals(status)) {
                    String filePath = file.getConvertedFilePath();
                    String fileName = file.getFileName();
                    String fileType = fileName.substring(fileName.lastIndexOf(".") + 1);
                    if (IndexConstant.FILE_TYPE_LIST.contains(fileType))
                        filePath = file.getFilePath();
                    filePaths.add(filePath.replace(storageProperties.getDefaultStorageProperties().getEndPoint() + "/", ""));
                }
            });
            KnowledgeBaseList kbFile = kbFiles.get(0);
            Integer parseType = kbFile.getParseType();
            if (ParseTypeEnums.FILE_PARSE.getCode().equals(parseType)) {
                //删除表
                chunnkDomainService.delFiles(primitiveName, filePaths);
                //删除table_summary_(摘要表)
                chunnkDomainService.delFiles(FileFieldEnums.TABLE_SUMMARY_PREFIX + primitiveName, filePaths);
                //删除 table_chunks_(chunk数据)
                chunnkDomainService.delFiles(FileFieldEnums.TABLE_CHUNKS_PREFIX + primitiveName, filePaths);
            }

            if (ParseTypeEnums.FAQ_PARSE.getCode().equals(parseType) || ParseTypeEnums.FAQ_PARSE.getCode().equals(parseType)) {
                //删除FAQ
                chunnkDomainService.deleteFaq(primitiveName, fileIds, null);
            }

        }
        return true;
    }

    /**
     * @param uploadFileParam
     * @param files
     * @param chunking        是否要chunk化
     * @return
     */
    @Override
    public Object uploadFileList(String uploadFileParam, MultipartFile[] files, boolean chunking) {
        UploadFileListReq uploadFileReq = JSONObject.parseObject(uploadFileParam, UploadFileListReq.class);
        uploadFileReq.setChunking(chunking);

        //校验文件列表是否有同名文件  返回异常:上传文件列表存在同名文件，请重新上传
        if (knowledgeBaseListDomainService.checkFileName(uploadFileReq.getFileList()))
            throw new ApplicationException(ErrCodeEnum.FILE_NAME_SAME_ERROR);

        AtomicInteger index = new AtomicInteger(0);
        uploadFileReq.getFileList().forEach(file -> {
            int current = index.getAndIncrement();
            file.setMultipartFile(files[current]);
            file.setChunking(chunking);
        });

        try {
            return dealUploadFileListRequest(uploadFileReq);
        } catch (Exception ex) {
            log.error(ex.getMessage(), ex);
            throw new ApplicationException(ErrCodeEnum.UPLOAD_FILE_ERROR);
        }
    }

    @Override
    public Object uploadFileList(String uploadFileParam, MultipartFile[] files) {
        UploadFileListReq uploadFileReq = JSONObject.parseObject(uploadFileParam, UploadFileListReq.class);

        //校验文件列表是否有同名文件  返回异常:上传文件列表存在同名文件，请重新上传
        if (knowledgeBaseListDomainService.checkFileName(uploadFileReq.getFileList()))
            throw new ApplicationException(ErrCodeEnum.FILE_NAME_SAME_ERROR);

        AtomicInteger index = new AtomicInteger(0);
        List<UploadFileListReq.UploadFile> fileList = Lists.newArrayList();
        uploadFileReq.getFileList().forEach(file -> {
            String fileName = file.getFileName();
            if (UrlKeywordChecker.containsUrlKeywords(fileName))
                throw new ApplicationException(ErrCodeEnum.FILE_NAME_ILLEGAL.getErrCode(), "【" + fileName + "】" + ErrCodeEnum.FILE_NAME_ILLEGAL.getErrMsg());
            if (!fileName.startsWith(EXCLUDE_FILENAME_PREFIX)) {
                int current = index.getAndIncrement();
                file.setMultipartFile(files[current]);
                file.setChunking(uploadFileReq.isChunking());
                fileList.add(file);
            }
        });
        uploadFileReq.setFileList(fileList);
        return dealUploadFileListRequest(uploadFileReq);

//        try {
//            return dealUploadFileListRequest(uploadFileReq);
//        } catch (Exception ex) {
//            log.error(ex.getMessage(), ex);
//            throw new ApplicationException(ErrCodeEnum.UPLOAD_FILE_ERROR);
//        }
    }

    private Object dealUploadFileListRequest(UploadFileListReq uploadFileReq) {
        Long kbId = uploadFileReq.getKbId();
        KnowledgeBase dbKnowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(dbKnowledgeBase)) {
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        }

        //查询并校验多版本模型
        modelInfoAppService.getSimpByModeName(dbKnowledgeBase.getModelName());

        uploadFileReq.setPrimitiveName(dbKnowledgeBase.getRealPrimitiveName());
        uploadFileReq.setPlatform(dbKnowledgeBase.getPlatform());

        List<KnowledgeBaseFileDTO> simpleFileList = uploadFileReq.getSimpleFileList();


        Set<String> existedFiles = Sets.newHashSet();
        List<KbFile> uploadKbFiles = Lists.newArrayList();
        Set<String> uploadingFiles = Sets.newHashSet();

        //拆分成非压缩文件列表和压缩文件列表
        dealNormalFiles(uploadFileReq, dbKnowledgeBase, existedFiles, uploadKbFiles, uploadingFiles);
        dealCompressedFiles(uploadFileReq, dbKnowledgeBase, existedFiles, uploadKbFiles, uploadingFiles);

        //入库 解析  抽取  文件修订时间
        List<KnowledgeBaseFileDTO> kbFileDTOs = Lists.newArrayList();
        if (!CollectionUtils.isEmpty(uploadKbFiles)) {
            uploadKbFiles.forEach(kbFile -> kbFile.setChunking(uploadFileReq.isChunking()));
            //图谱解析
            Integer fileListType = uploadFileReq.getFileListType();
            if (FileListTypeEnums.GRAPH_LIST.getCode().equals(fileListType)) {
                kbFileDTOs = graphParse(dbKnowledgeBase, uploadKbFiles, uploadFileReq);
            } else  //文件解析和抽取
                kbFileDTOs = fileParseAndExtract(dbKnowledgeBase, uploadKbFiles, uploadFileReq);
        }
        buildUploadResponse(simpleFileList, existedFiles, uploadingFiles, kbFileDTOs);
        if (!CollectionUtils.isEmpty(existedFiles)) {
            List<KnowledgeBaseFileDTO> failFiles = Lists.newArrayList();
            existedFiles.forEach(fileName -> {
                KnowledgeBaseFileDTO fileDTO = new KnowledgeBaseFileDTO();
                fileDTO.setFileName(fileName);
                fileDTO.setUploadStatus(2);//失败
                fileDTO.setMessage(ErrCodeEnum.FILE_NAME_SAME_ERROR.getErrMsg());
                failFiles.add(fileDTO);
            });
            CommonResponse<Object> failResponse = CommonResponse.fail(ErrCodeEnum.FILE_NAME_SAME_ERROR);
            failResponse.setData(failFiles);
            return failResponse;
        }
        return kbFileDTOs;

    }

    private void buildUploadResponse(List<KnowledgeBaseFileDTO> simpleFileList, Set<String> existedFiles, Set<String> uploadingFiles, List<KnowledgeBaseFileDTO> kbFileDTOs) {
        simpleFileList.forEach(file -> {
            if (existedFiles.contains(file.getFileName())) {
                file.setUploadStatus(2);//失败
                file.setMessage(ErrCodeEnum.FILE_NAME_SAME_ERROR.getErrMsg());
            } else {
                if (uploadingFiles.contains(file.getFileName())) {
                    Optional<KnowledgeBaseFileDTO> first = kbFileDTOs.stream().filter(kbFile -> kbFile.getFileName().equals(file.getFileName())).findFirst();
                    if (first.isPresent()) {
                        first.get().setUploadStatus(1);//成功
                        first.get().setFilePath(first.get().getFilePath());
                    }
                }
            }
        });
    }

    private void dealCompressedFiles(UploadFileListReq uploadFileReq, KnowledgeBase dbKnowledgeBase, Set<String> existedFiles, List<KbFile> uploadKbFiles, Set<String> uploadingFiles) {
        UploadFileListReq compressedFileListReq = uploadFileReq.swallowCopy();
        uploadFileReq.getFileList().forEach(f -> {
            if (ArrayUtils.contains(APPROVED_COMPRESSED_FILE_LIST, getFileExtension(f.getFileName().toLowerCase(Locale.ROOT)))) {
                compressedFileListReq.getFileList().add(f);
            }
        });

        //上传压缩文件列表
        if (!CollectionUtils.isEmpty(compressedFileListReq.getFileList())) {
            uploadCompressedFileList(compressedFileListReq, dbKnowledgeBase, existedFiles, uploadKbFiles, uploadingFiles);
        }
    }

    private void dealNormalFiles(UploadFileListReq uploadFileReq, KnowledgeBase dbKnowledgeBase, Set<String> existedFiles, List<KbFile> uploadKbFiles, Set<String> uploadingFiles) {
        UploadFileListReq nonCompressedFileListReq = uploadFileReq.swallowCopy();
        uploadFileReq.getFileList().forEach(f -> {
            if (ArrayUtils.contains(APPROVED_NORMAL_FILE_LIST, getFileExtension(f.getFileName().toLowerCase(Locale.ROOT))) && !f.getFileName().startsWith(EXCLUDE_FILENAME_PREFIX)) {
                nonCompressedFileListReq.getFileList().add(f);
            }
        });
        //上传非压缩文件列表
        if (!CollectionUtils.isEmpty(nonCompressedFileListReq.getFileList())) {
            uploadNonCompressedFileList(nonCompressedFileListReq, dbKnowledgeBase, existedFiles, uploadKbFiles, uploadingFiles);
        }
    }

    private List<KnowledgeBaseFileDTO> graphParse(KnowledgeBase dbKnowledgeBase, List<KbFile> kbFiles, UploadFileListReq uploadFileReq) {
        String primitiveName = dbKnowledgeBase.getPrimitiveName();
        Long kbId = dbKnowledgeBase.getId();
        Integer parseType = uploadFileReq.getFileListType();
        boolean chunking = uploadFileReq.isChunking();
        List<KnowledgeBaseFileDTO> knowledgeBaseList = addKnowledgeBaseList(kbId, dbKnowledgeBase.getSourceUrl(), kbFiles, parseType, Arrays.asList(parseType), chunking);
        FilesParseReq filesParseReq = buildFilesParseParam(knowledgeBaseList, kbId, primitiveName, chunking);
        List<FilesParseReq.File> files = filesParseReq.getFiles();
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);

//        Integer fileListType = uploadFileReq.getFileListType();
//        Boolean isExtract = uploadFileReq.getIsExtract();
//        Boolean isParse = uploadFileReq.getIsParse();
        Boolean saveTxt = uploadFileReq.getSaveTxt();
        String platform = uploadFileReq.getPlatform();

        Boolean isGraphParse = uploadFileReq.getIsGraphParse();

        //解析任务
        List<FileParseTask> taskList = Lists.newArrayList();
        //图谱解析和文件解析id
        List<Long> fileIds = Lists.newArrayList();
        //图解析
        if (uploadFileReq.getIsGraphParse()) {
            for (FilesParseReq.File file : files) {
                if (isGraphParse) {
                    fileIds.add(file.getFileId());
                    //解析任务详情
                    FileParseTaskInfo taskInfo = BeanUtil.copyProperties(filesParseReq, FileParseTaskInfo.class);
                    taskInfo.setFiles(Collections.singletonList(BeanUtil.copyProperties(file, FileParseTaskInfo.File.class)));
                    taskInfo.setIsExtract(false);
                    taskInfo.setUserName(UserContext.getUser().getUserName());
                    taskInfo.setUserId(UserContext.getUser().getUserId());
                    taskInfo.buildKbConf(knowledgeBase.getConfig());
                    taskInfo.setIndexName(primitiveName);
                    taskInfo.setSaveTxt(saveTxt);
                    taskInfo.setPrimitiveName(primitiveName);
                    taskInfo.setNeedChunk(chunking);
                    taskInfo.adjustByPlatform(platform, chunking);
                    taskInfo.setIsGraphParse(isGraphParse);
                    taskInfo.setParseType(parseType);

                    User user = UserContext.getUser();
                    String userName = user.getUserName();
                    //解析任务
                    FileParseTask fileParseTask = new FileParseTask();
                    fileParseTask.setKbId(knowledgeBase.getId());
                    fileParseTask.setKbName(knowledgeBase.getPrimitiveName());
                    fileParseTask.setFileId(file.getFileId());
                    fileParseTask.setFileName(file.getFileName());
                    fileParseTask.setTaskInfo(JSON.toJSONString(taskInfo));
                    fileParseTask.setStatus(ParseTaskStatusEnums.PENDING.getCode());
                    fileParseTask.setRetryLimit(retryLimit);
                    fileParseTask.setRetryTimes(0);
                    fileParseTask.setCreateBy(userName);
                    fileParseTask.setModifyBy(userName);
                    fileParseTask.setGmtCreate(new Date());
                    // fileParseTask.setStartTime(fileParseTask.getGmtCreate());
                    fileParseTask.setGmtModified(fileParseTask.getGmtCreate());
                    taskList.add(fileParseTask);
                }
            }
        }

        //如果是图谱解析，将状态更新为抽取中
        knowledgeBaseListDomainService.updateGraphExtractByIds(fileIds, GraphParseStatusEnums.PARSE_ING.getValue());
        //解析文件解析状态
        knowledgeBaseListDomainService.updateParseStatusByIds(fileIds, KbFileStatusEnums.PARSE_WAIT.getValue(), true);
        //添加解析任务
        fileParseTaskDomainService.saveBatch(taskList);

        return knowledgeBaseList;
    }

    private String getFileExtension(String fileName) {
        return fileName.substring(fileName.lastIndexOf(".") + 1);
    }

    private void uploadNonCompressedFileList(UploadFileListReq uploadFileReq, KnowledgeBase dbKnowledgeBase, Set<String> existedFiles, List<KbFile> uploadKbFiles, Set<String> uploadingFiles) {
        //查询知识库的文件
        List<KnowledgeBaseList> existedKbFiles = knowledgeBaseListDomainService.findFileByKbIdAndType(
                uploadFileReq.getKbId(), uploadFileReq.getFileListType());

        Iterator<UploadFileListReq.UploadFile> iterator = uploadFileReq.getFileList().iterator();
        while (iterator.hasNext()) {
            UploadFileListReq.UploadFile uploadFile = iterator.next();
            //知识库的文件是否和上传的文件有重复的,如果有重复的文件,先上传正常的文件，然后返回同名文件
            if (existedKbFiles.stream().anyMatch(kbFile -> kbFile.getFileName().equals(uploadFile.getFileName())) &&
                    uploadFile.getType() == null) {
                existedFiles.add(StringUtils.isEmpty(uploadFile.getSourceUrl()) ? uploadFile.getFileName() :
                        uploadFile.getSourceUrl() + "|" + uploadFile.getFileName());
                iterator.remove();
            } else {
                //和其他url是否有重复的上传文件,如果有重复的文件,先上传正常的文件，然后返回同名文件
                if (uploadingFiles.stream().anyMatch(f -> f.equals(uploadFile.getFileName()))) {
                    existedFiles.add(StringUtils.isEmpty(uploadFile.getSourceUrl()) ? uploadFile.getFileName() :
                            uploadFile.getSourceUrl() + "|" + uploadFile.getFileName());
                    iterator.remove();
                }
            }
        }

        //识别待上传文件多版本&待上传文件和知识库中的文件多版本识别
        List<KbFile> kbFiles = knowledgeBaseListDomainService.recognise(uploadFileReq);

        //文件上传
        for (KbFile kbFile : kbFiles) {
            kbFileUpload(kbFile, dbKnowledgeBase.getRealPrimitiveName(), uploadFileReq.getPlatform(), UserContext.getUser().getUserId());
            uploadingFiles.add(kbFile.getFileName());
            uploadKbFiles.add(kbFile);
        }
    }

    private void uploadCompressedFileList(UploadFileListReq uploadFileReq, KnowledgeBase dbKnowledgeBase, Set<String> existedFiles, List<KbFile> uploadKbFiles, Set<String> uploadingFiles) {
        for (UploadFileListReq.UploadFile uploadFile : uploadFileReq.getFileList()) {
            handleArchive(uploadFile, uploadFileReq, dbKnowledgeBase, existedFiles, uploadKbFiles, uploadingFiles, null);
        }
    }

    private void handleArchive(UploadFileListReq.UploadFile uploadFile, UploadFileListReq uploadFileReq, KnowledgeBase dbKnowledgeBase, Set<String> existedFiles, List<KbFile> uploadKbFiles, Set<String> uploadingFiles, String parentPath) {
        String fileName = uploadFile.getMultipartFile().getOriginalFilename();
        assert fileName != null;
        String archiveType = getArchiveType(fileName);
        if (archiveType == null) {
            throw new ApplicationException(ErrCodeEnum.COMPRESSED_FILE_TYPE_ERROR);
        }

        //查询知识库的文件
        List<KnowledgeBaseList> existedKbFiles = knowledgeBaseListDomainService.findFileByKbIdAndType(uploadFileReq.getKbId(), uploadFileReq.getFileListType());

        //查询最新版本(父文件名维度)
        Boolean isExtract = uploadFileReq.getIsExtract();
        Boolean isParse = uploadFileReq.getIsParse();
        Integer fileListType = uploadFileReq.getFileListType();
        if (FileListTypeEnums.FILE_LIST.getCode().equals(fileListType)) {
            if (isExtract && !isParse)
                fileListType = FileListTypeEnums.FAQ_LIST.getCode();
            else if (isExtract && isParse)
                fileListType = null;
        }
        List<KnowledgeBaseList> kbFiles = knowledgeBaseListDomainService.findFileMaxVersion(uploadFileReq.getKbId(), fileListType);
        try (InputStream inputStream = new ByteArrayInputStream(uploadFile.getMultipartFile().getBytes());
             ArchiveInputStream archiveInputStream = new ArchiveStreamFactory().createArchiveInputStream(archiveType, inputStream)) {
            ArchiveEntry entry;
            Map<String, Long> folderInfoMap = Maps.newHashMap(); // key是目录名（以/结尾）; value是对应的folderId
            while ((entry = archiveInputStream.getNextEntry()) != null) {
                String entryName = entry.getName();
                if (StringUtils.isNotBlank(parentPath)) {
                    if (entry.isDirectory()) {
                        parentPath = parentPath + entryName;
                    } else {
                        entryName = parentPath + entryName.substring(entryName.lastIndexOf("/") + 1);
                    }
                }

                //压缩包
                if (ArrayUtils.contains(APPROVED_COMPRESSED_FILE_LIST, getFileExtension(entryName.toLowerCase(Locale.ROOT)))) {
                    if (StringUtils.isEmpty(parentPath))
                        parentPath = entryName.substring(0, entryName.lastIndexOf("/") + 1);
                    uploadFile.setFileName(getRawFileName(entryName));
                    try (ByteArrayOutputStream baos = new ByteArrayOutputStream()) {
                        IOUtils.copy(archiveInputStream, baos);
                        byte[] entryContent = baos.toByteArray();
                        MultipartFile multipartFile = new MockMultipartFile(
                                "files",
                                fileName,
                                MediaType.APPLICATION_OCTET_STREAM_VALUE,
                                new ByteArrayInputStream(entryContent)
                        );
                        uploadFile.setMultipartFile(multipartFile);
                        handleArchive(uploadFile, uploadFileReq, dbKnowledgeBase, existedFiles, uploadKbFiles, uploadingFiles, parentPath);
                        parentPath = null;
                        continue;
                    }
                }

                //文件夹
                if (entry.isDirectory()) {
                    String folder = entryName;
                    if (StringUtils.isNotBlank(parentPath))
                        folder = parentPath;
                    FolderInfo folderInfo = createFolderIfNotExists(uploadFileReq.getKbId(), uploadFileReq.getFileListType(), uploadFileReq.getFolderId(), folder);
                    folderInfoMap.put(folder, folderInfo.getId());
                    continue;
                }
                String rawFileName = getRawFileName(entryName);
                if (rawFileName.startsWith(EXCLUDE_FILENAME_PREFIX))
                    continue;
                // 压缩包里重复的文件二次上传，则只处理二次上传的文件
                if (uploadFile.getCompressedFileList() != null) {
                    String finalEntryName = entryName;
                    if (uploadFile.getCompressedFileList().stream().noneMatch(
                            c -> c.getFilePath().equals(finalEntryName) &&
                                    (c.getType() == UploadFileTypeEnums.OVERWRITE || c.getType() == UploadFileTypeEnums.NEWVERSION))) {
                        continue;
                    }
                } else {
                    //知识库的文件是否和上传的文件有重复的,如果有重复的文件,先上传正常的文件，然后返回同名文件
                    if (existedKbFiles.stream().anyMatch(kbFile -> kbFile.getFileName().equals(rawFileName))) {
                        existedFiles.add(StringUtils.isEmpty(uploadFile.getSourceUrl()) ? fileName + ":" + entryName :
                                uploadFile.getSourceUrl() + "|" + fileName + ":" + entryName);
                        continue;
                    }

                    //压缩包里是否有重复的上传文件,如果有重复的文件,先上传正常的文件，然后返回同名文件
                    if (uploadingFiles.stream().anyMatch(f -> f.equals(rawFileName))) {
                        existedFiles.add(StringUtils.isEmpty(uploadFile.getSourceUrl()) ? fileName + ":" + entryName :
                                uploadFile.getSourceUrl() + "|" + fileName + ":" + entryName);
                        continue;
                    }
                }

                //识别待上传文件多版本&待上传文件和知识库中的文件多版本识别
                KbFile kbFile = knowledgeBaseListDomainService.recogniseCompressedFile(
                        uploadFile, uploadFileReq, entryName, rawFileName, folderInfoMap, kbFiles);

                try (ByteArrayOutputStream baos = new ByteArrayOutputStream()) {
                    IOUtils.copy(archiveInputStream, baos);
                    byte[] entryContent = baos.toByteArray();
                    MultipartFile multipartFile = new MockMultipartFile(
                            "files",
                            fileName,
                            MediaType.APPLICATION_OCTET_STREAM_VALUE,
                            new ByteArrayInputStream(entryContent)
                    );
                    kbFile.setMultipartFile(multipartFile);
                    kbFileUpload(kbFile, dbKnowledgeBase.getRealPrimitiveName(), uploadFileReq.getPlatform(), UserContext.getUser().getUserId());

                    uploadingFiles.add(rawFileName);
                    uploadKbFiles.add(kbFile);
                }
            }
        } catch (Exception ex) {
            log.error(ex.getMessage(), ex);
            throw new ApplicationException(ErrCodeEnum.PUT_OBJECT_ERROR);
        }
    }

    private FolderInfo createFolderIfNotExists(Long kbId, Integer type, Long baseFolderId, String entryName) {
        String fullPath = entryName; // 完整目录名（包含结尾/)
        if (baseFolderId != null) {
            FolderInfo baseFolderInfo = folderInfoDomainService.findById(baseFolderId);
            fullPath = baseFolderInfo.getFullPath() + entryName;
        }
        String lastSegment = FilenameUtils.getName(fullPath.substring(0, fullPath.length() - 1)); // 当前目录名称(不包含结尾/)
        String parentSegment = fullPath.substring(0, fullPath.lastIndexOf(lastSegment + "/")); // ""或父目录名称（以/结尾）

        // 查询文件夹表里是否已有该文件夹数据
        FolderInfo folderInfo = folderInfoDomainService.getByKbIdAndFullPath(kbId, fullPath);
        if (folderInfo == null) {
            // 查询父文件夹信息
            Long parentFolderId = null;
            if (StringUtils.isNotEmpty(parentSegment)) {
                FolderInfo parentFolderInfo = folderInfoDomainService.getByKbIdAndFullPath(kbId, parentSegment);
                parentFolderId = parentFolderInfo.getId();
            }
            // 文件夹表里写入当前文件夹数据
            folderInfo = new FolderInfo();
            folderInfo.setName(lastSegment);
            folderInfo.setKbId(kbId);
            folderInfo.setType(type);
            folderInfo.setParentId(parentFolderId);
            folderInfo.setStatus(FolderSatusEnums.NORMAL.getCode());
            folderInfo.setFullPath(fullPath);
            folderInfoDomainService.save(folderInfo);
        }

        return folderInfo;
    }

    private String getArchiveType(String fileName) {
        if (fileName.endsWith(".zip")) {
            return "zip";
        } else if (fileName.endsWith(".tar")) {
            return "tar";
        }
        return null;
    }

    private String getRawFileName(String entryName) {
        if (entryName.indexOf('/') < 0) {
            return entryName;
        } else {
            return entryName.substring(entryName.lastIndexOf('/') + 1);
        }
    }


    private void kbFileUpload(KbFile kbFile, String primitiveName, String platform, String userId) {
        String folder = getFolder(platform, userId, primitiveName, kbFile.getParentFileName(), kbFile.getVersion());
        try {
            String fileName = kbFile.getFileName();
            String fileType = fileName.substring(fileName.lastIndexOf(".") + 1);
            fileType = fileType.toLowerCase(Locale.ROOT);
            kbFile.setFileName(kbFile.getConvertedFileName(fileType));
            FileInfo fileInfo = fileStorageUtils.putObject(folder, kbFile.getMultipartFile(), kbFile.getFileName(), null);
            kbFile.setFileSize(fileInfo.getFileSize());
            kbFile.setObjectName(getObjectName(platform, folder, kbFile.getParentFileName(), kbFile.getVersion(), kbFile.getFileName()));
//            //pdf  excel  csv 图片不需要转
//            if (kbFile.isConvertedFile(fileType)) {
//                //原文件类型
//                kbFile.setConvertedObjectName(fileType);
//            }
        } catch (FileStorageException ex) {
            log.error(ex.getMessage(), ex);
            throw new ApplicationException(ErrCodeEnum.PUT_OBJECT_ERROR);
        }
//        catch (IOException ex) {
//            log.error(ex.getMessage(), ex);
//            throw new ApplicationException(ErrCodeEnum.CONVERT_FILE_ERROR);
//        }
//        catch (OfficeException ex) {
//            log.error(ex.getMessage(), ex);
//            throw new ApplicationException(ErrCodeEnum.LIBREOFFICE_ERROR);
//        }
    }

    private List<BizLabel> findSuperiorLabel(Long targetId, Long folderId, BizTypeEnums bizTypeEnums) {
        List<BizLabel> fullFolderLabels = findFullFolderLabels(folderId);
        fullFolderLabels.forEach(label -> {
            label.setTargetId(targetId);
            label.setId(null);
            label.setBizType(bizTypeEnums.getCode());
        });
        return fullFolderLabels;
    }

    private List<BizLabel> findFullFolderLabels(Long folderId) {
        List<FolderInfo> folderInfos = folderInfoDomainService.findParentIdsById(folderId);
        if (!CollectionUtils.isEmpty(folderInfos)) {
            return bizLabelDomainService.findByTargetIds(getTargetIdsByFolderList(folderInfos));
        }
        return List.of();
    }

    private List<Long> getTargetIdsByFolderList(List<FolderInfo> folderInfos) {
        List<Long> targetIds = Lists.newArrayList();
        targetIds.addAll(folderInfos.stream().map(FolderInfo::getId).toList());
        targetIds.add(folderInfos.get(0).getKbId());
        return targetIds;
    }

    /**
     * @param platform       平台标识
     * @param userId         用户id
     * @param primitiveName  此为kbName
     * @param parentFileName 父文件夹
     * @param version        版本
     * @return String
     */
    private String getFolder(String platform, String userId, String primitiveName, String parentFileName, String version) {
        if (!platform.equals(PlatFormEnums.RAG_QA.getCode())) {
            return String.format("%s/%s/%s/%s/%s/", platform, userId, primitiveName, parentFileName, version);
        } else {
            return String.format("%s/%s/%s/", primitiveName, parentFileName, version);
        }
    }

    private String getObjectName(String platform, String folder, String parentFileName, String version, String fileName) {
        return String.format("%s/%s/%s", parentFileName, version, fileName);
//        if (!platform.equals(PlatFormEnums.RAG_QA.getCode())) {
//            return String.format("%s/%s", folder, fileName);
//        } else {
//            return String.format("%s/%s/%s", parentFileName, version, fileName);
//        }
    }

    private List<KnowledgeBaseFileDTO> fileParseAndExtract(KnowledgeBase dbKnowledgeBase, List<KbFile> kbFiles, UploadFileListReq uploadFileReq) {
        Integer fileListType = uploadFileReq.getFileListType();
        Boolean isExtract = uploadFileReq.getIsExtract();
        Boolean isParse = uploadFileReq.getIsParse();
        Boolean saveTxt = uploadFileReq.getSaveTxt();
        String platform = uploadFileReq.getPlatform();
        boolean chunking = uploadFileReq.isChunking();

        String primitiveName = dbKnowledgeBase.getPrimitiveName();
        Long kbId = dbKnowledgeBase.getId();
        Integer parseType = null;
        List<Integer> parseTypes = null;
        if (FileListTypeEnums.FILE_LIST.getCode().equals(fileListType)) {
            parseType = ParseTypeEnums.FILE_PARSE.getCode();
            parseTypes = Lists.newArrayList(ParseTypeEnums.FILE_PARSE.getCode());
            if (isParse && isExtract) {
                parseType = ParseTypeEnums.FAQ_FILE_PARSE.getCode();
                parseTypes = Lists.newArrayList(ParseTypeEnums.FILE_PARSE.getCode(), ParseTypeEnums.FAQ_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode());
            } else if (!isParse && isExtract) {
                parseType = ParseTypeEnums.FAQ_PARSE.getCode();
                parseTypes = Lists.newArrayList(ParseTypeEnums.FAQ_PARSE.getCode());
            }
        } else if (FileListTypeEnums.FAQ_LIST.getCode().equals(fileListType)) {
            parseType = ParseTypeEnums.FAQ_PARSE.getCode();
            parseTypes = Lists.newArrayList(ParseTypeEnums.FAQ_PARSE.getCode());
        } else if (FileListTypeEnums.DOC_QA.getCode().equals(fileListType)) {
            parseType = ParseTypeEnums.DOC_QA.getCode();
            parseTypes = Lists.newArrayList(ParseTypeEnums.FAQ_PARSE.getCode());
        }
        List<KnowledgeBaseFileDTO> knowledgeBaseList = addKnowledgeBaseList(kbId, dbKnowledgeBase.getSourceUrl(), kbFiles, parseType, parseTypes, chunking);
        FilesParseReq filesParseReq = buildFilesParseParam(knowledgeBaseList, kbId, primitiveName, chunking);
        List<FilesParseReq.File> files = filesParseReq.getFiles();
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);

        //文件多版本解析(仅文件解析)
        if (!isExtract && (ParseTypeEnums.FILE_PARSE.getCode().equals(parseType) || ParseTypeEnums.FAQ_FILE_PARSE.getCode().equals(parseType)))
            fileAppService.fileMultiversionParse(
                    kbId,
                    knowledgeBaseList.stream().map(KnowledgeBaseFileDTO::getId).collect(Collectors.toList()),
                    MultiversionParseEnums.FILENAME,
                    Arrays.asList(ParseTypeEnums.FILE_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode()));

        //解析任务
        List<FileParseTask> taskList = Lists.newArrayList();
        //解析文件id
        List<Long> parseFileIds = Lists.newArrayList();
        //FAQ抽取的文件id
        List<Long> extractFileIds = Lists.newArrayList();

        for (FilesParseReq.File file : files) {
            //文件抽取，必须先解析
            if (isExtract) {
                isParse = true;
                extractFileIds.add(file.getFileId());
            }
            if (isParse) {
                parseFileIds.add(file.getFileId());
                //解析任务详情
                FileParseTaskInfo taskInfo = BeanUtil.copyProperties(filesParseReq, FileParseTaskInfo.class);
                taskInfo.setFiles(Collections.singletonList(BeanUtil.copyProperties(file, FileParseTaskInfo.File.class)));
                taskInfo.setIsExtract(isExtract);
                taskInfo.setUserName(UserContext.getUser().getUserName());
                taskInfo.setUserId(UserContext.getUser().getUserId());
                taskInfo.buildKbConf(knowledgeBase.getConfig());
                taskInfo.setIndexName(primitiveName);
                taskInfo.setSaveTxt(saveTxt);
                taskInfo.setPrimitiveName(primitiveName);
                taskInfo.setNeedChunk(chunking);
                taskInfo.adjustByPlatform(platform, chunking);
                taskInfo.setParseType(parseType);

                User user = UserContext.getUser();
                String userName = user.getUserName();
                //解析任务
                FileParseTask fileParseTask = new FileParseTask();
                fileParseTask.setKbId(knowledgeBase.getId());
                fileParseTask.setKbName(knowledgeBase.getPrimitiveName());
                fileParseTask.setFileId(file.getFileId());
                fileParseTask.setFileName(file.getFileName());
                fileParseTask.setTaskInfo(JSON.toJSONString(taskInfo));
                fileParseTask.setStatus(ParseTaskStatusEnums.PENDING.getCode());
                fileParseTask.setRetryLimit(retryLimit);
                fileParseTask.setRetryTimes(0);
                fileParseTask.setCreateBy(userName);
                fileParseTask.setModifyBy(userName);
                fileParseTask.setGmtCreate(new Date());
                // fileParseTask.setStartTime(fileParseTask.getGmtCreate());
                fileParseTask.setGmtModified(fileParseTask.getGmtCreate());
                taskList.add(fileParseTask);
            }
        }
        //解析文件更新为等待状态
        knowledgeBaseListDomainService.updateParseStatusByIds(parseFileIds, KbFileStatusEnums.PARSE_WAIT.getValue(), true);
        //FAQ抽取，将状态更新为抽取中
        knowledgeBaseListDomainService.updateExtractStatusByIds(extractFileIds, FaqExtractStatusEnums.EXTRACT_ING.getValue());
        //添加解析任务
        fileParseTaskDomainService.saveBatch(taskList);
        return knowledgeBaseList;
    }

    @Override
    public Set<String> precheck(List<String> fileNameList) {
        if (CollectionUtils.isEmpty(fileNameList))
            return null;
        List<String> tmpFileNames = Lists.newArrayList();
        Set<String> repeatFileNames = Sets.newHashSet();
        for (String fileName : fileNameList) {
            if (!tmpFileNames.contains(fileName))
                tmpFileNames.add(fileName);
            else
                repeatFileNames.add(fileName);
        }
        return repeatFileNames;
    }

    @Override
    public Page<KnowledgeBaseFileDTO> listNew(KnowledgeBaseFileQueryReq req) {
        Long kbId = req.getKbId();
        Integer fileListType = req.getFileListType();
        String fuzzy = req.getFuzzy();
        Integer status = req.getStatus();
        Integer faqExtractStatus = req.getFaqExtractStatus();
        Integer showType = req.getShowType();
        Long pageNo = req.getPageNo();
        Long pageSize = req.getPageSize();
        Page<KnowledgeBaseList> page = knowledgeBaseListDomainService
                .parentList(kbId, fileListType, fuzzy, status, faqExtractStatus, showType, null, pageNo, pageSize);
        Integer basicPermission = knowledgeBaseDomainService.getHighestPermission(kbId);
        Page<KnowledgeBaseFileDTO> res = new PageDTO<>();
        BeanUtil.copyProperties(page, res);
        res.setRecords(BeanUtil.copyToList(page.getRecords(), KnowledgeBaseFileDTO.class));

        //查询子文件
        req.setPageNo(1L);
        req.setPageSize(200L);
        List<KnowledgeBaseFileDTO> parentRecords = res.getRecords();
        parentRecords.forEach(parentRecord -> {
            req.setParentFileName(parentRecord.getParentFileName());
            Page<KnowledgeBaseFileDTO> kbFilePage = this.list(req);
            List<KnowledgeBaseFileDTO> records = kbFilePage.getRecords();
            parentRecord.setPermission(basicPermission);
            buildFolder(records, basicPermission);
            setFilesPermission(kbId, basicPermission, records, fileListType);
            parentRecord.setKbFiles(records);
        });
        setFilesPermission(kbId, basicPermission, parentRecords, fileListType);
        return res;
    }

    @Override
    public Page<KnowledgeBaseFileDTO> multipleVersion(KnowledgeBaseFileQueryReq req) {
        List<String> kbNames = req.getKbNames();

        List<KnowledgeBase> knowledgeBases = knowledgeBaseDomainService.findByPrimitiveNames(kbNames);
        if (CollectionUtils.isEmpty(knowledgeBases))
            return null;
        List<Long> kbIds = knowledgeBases.stream().map(KnowledgeBase::getId).toList();
        Long pageNo = req.getPageNo();
        Long pageSize = req.getPageSize();
        Page<KnowledgeBaseList> page = knowledgeBaseListDomainService.parentList(
                null, FileListTypeEnums.FILE_LIST.getCode(),
                null, null, null, 2, kbIds, pageNo, pageSize);
        Page<KnowledgeBaseFileDTO> res = new PageDTO<>();
        BeanUtil.copyProperties(page, res);
        res.setRecords(BeanUtil.copyToList(page.getRecords(), KnowledgeBaseFileDTO.class));

        //查询子文件
        List<KnowledgeBaseFileDTO> parentRecords = res.getRecords();
        parentRecords.forEach(parentRecord -> {
            String parentFileName = parentRecord.getParentFileName();
            Page<KnowledgeBaseList> knowledgeBasePage = knowledgeBaseListDomainService.list(parentRecord.getKbId(), FileListTypeEnums.FILE_LIST.getCode(), null, null, null, parentFileName, 1L, 1000L);
            parentRecord.setKbFiles(BeanUtil.copyToList(knowledgeBasePage.getRecords(), KnowledgeBaseFileDTO.class));
        });
        return res;
    }

    private void buildFolder(List<KnowledgeBaseFileDTO> knowledgeBaseFileDTOS, Integer basicPermission) {
        if (!CollectionUtils.isEmpty(knowledgeBaseFileDTOS)) {
            knowledgeBaseFileDTOS.forEach(kbFile -> {
                Long folderId = kbFile.getFolderId();
                kbFile.setPermission(basicPermission);
                if (!Objects.isNull(folderId)) {
                    FolderInfo folderInfo = folderInfoDomainService.findById(folderId);
                    if (Objects.nonNull(folderInfo))
                        kbFile.setFullFolderPath(folderInfo.getFullPath() + kbFile.getFileName());
                } else
                    kbFile.setFullFolderPath(kbFile.getFileName());
            });
        }
    }

    @Override
    public Boolean filesReviseDate(Long fileId, String reviseDate) {
        if (Objects.isNull(fileId))
            return false;
        KnowledgeBaseList knowledgeBaseFile = knowledgeBaseListDomainService.findById(fileId);
        if (Objects.isNull(knowledgeBaseFile))
            throw new ApplicationException(ErrCodeEnum.KB_FILE_NOT_EXISTS_ERROR);
        Integer status = knowledgeBaseFile.getStatus();
        if (!KbFileStatusEnums.PARSE_SUCCESS.getValue().equals(status))
            throw new ApplicationException(ErrCodeEnum.FILE_NO_PARSE);
        List<FileChunkDTO> fileChunks = getFileChunks(fileId, null, null);
        List<Long> chunkIds = fileChunks.stream().map(FileChunkDTO::getId).collect(Collectors.toList());
        if (!CollectionUtils.isEmpty(chunkIds)) {
            Long kbId = knowledgeBaseFile.getKbId();
            KnowledgeBase kb = knowledgeBaseDomainService.findByKbId(kbId);
            String primitiveName = kb.getPrimitiveName();
            JSONObject reviseDateParam = buildReviseDateParam(primitiveName, chunkIds, "revise_date", reviseDate);
            //修改向量数据中的修订时间
            remoteFileUtils.faqUpdateField(JSONObject.toJSONString(reviseDateParam));
            //更新es中的数据
            String resp = remoteFileUtils.updateFieldteEs(JSONObject.toJSONString(reviseDateParam));
            JSONObject respJson = JSONObject.parseObject(resp);
            if (!Objects.equals(respJson.getInteger("code"), 200))
                throw new ApplicationException(ErrCodeEnum.UPDATE_ES_ERROR);
        }
        knowledgeBaseFile.setReviseDate(reviseDate);
        knowledgeBaseListDomainService.update(knowledgeBaseFile);
        return true;
    }

    private JSONObject buildReviseDateParam(String primitiveName, List<Long> pks, String colName, Object colValue) {
        JSONObject faqReq = new JSONObject();
        faqReq.put("index_name", primitiveName);
        faqReq.put("pk", pks);
        faqReq.put("col_name", colName);
        faqReq.put("col_value", colValue);
        return faqReq;
    }

    @Override
    public Boolean chunkChange(ChunkChangeReq chunkChangeReq) {
        Long fileId = chunkChangeReq.getFileId();
        Long oldChunkId = chunkChangeReq.getOldChunkId();
        Long newChunkId = chunkChangeReq.getNewChunkId();
        Long imageChunkId = chunkChangeReq.getImageChunkId();

        KnowledgeBaseList knowledgeBaseFile = knowledgeBaseListDomainService.findById(fileId);
        if (Objects.isNull(knowledgeBaseFile))
            throw new ApplicationException(ErrCodeEnum.KB_FILE_NOT_EXISTS_ERROR);
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(knowledgeBaseFile.getKbId());
        if (Objects.isNull(knowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);

        String primitiveName = knowledgeBase.getPrimitiveName();
        FileChunkDTO oldChunk = getChunkByPk(primitiveName, Collections.singletonList(oldChunkId)).get(0);
        FileChunkDTO newChunk = getChunkByPk(primitiveName, Collections.singletonList(newChunkId)).get(0);
        List<FileChunkDTO> imageChunks = getChunkByPk(primitiveName, Collections.singletonList(imageChunkId));
        FileChunkDTO imageChunk = CollectionUtils.isEmpty(imageChunks) ? null : imageChunks.get(0);

        List<Long> oldPicChunkIds = oldChunk.getPicChunkIdList();
        List<Long> newPicChunkIds = newChunk.getPicChunkIdList();

        oldPicChunkIds.remove(imageChunkId);
        newPicChunkIds.add(imageChunkId);
        //更新chunk中pic_chunk_ids字段
        updateChunkField(primitiveName, Collections.singletonList(oldChunkId), "pic_children_id_list", oldPicChunkIds);
        updateChunkField(primitiveName, Collections.singletonList(newChunkId), "pic_children_id_list", newPicChunkIds);
        //更新图片url
        if (Objects.nonNull(imageChunk)) {
            String imagePath = imageChunk.getImagePath();
            List<String> oldPicUrlList = oldChunk.getPicUrlList();
            List<String> newPicUrlList = newChunk.getPicUrlList();
            oldPicUrlList.remove(imagePath);
            newPicUrlList.add(imagePath);
            updateChunkField(primitiveName, Collections.singletonList(oldChunkId), "pic_url_list", oldPicUrlList);
            updateChunkField(primitiveName, Collections.singletonList(newChunkId), "pic_url_list", newPicUrlList);
        }
        return true;
    }

    @Override
    public Object importUrlList(String importUrlListParam) {
        UploadFileListReq uploadFileReq = JSONObject.parseObject(importUrlListParam, UploadFileListReq.class);
        //校验url列表是否有重复url
        HashSet<String> set = new HashSet<>();
        uploadFileReq.getFileList().forEach(f -> set.add(f.getSourceUrl()));
        if (set.size() != uploadFileReq.getFileList().size())
            throw new ApplicationException(ErrCodeEnum.URL_SAME_ERROR);

        //校验文件列表是否有同名文件  返回异常:上传文件列表存在同名文件，请重新上传
        if (knowledgeBaseListDomainService.checkFileName(uploadFileReq.getFileList()))
            throw new ApplicationException(ErrCodeEnum.FILE_NAME_SAME_ERROR);

        List<UploadFileListReq.UploadFile> fileList = uploadFileReq.getFileList();
        for (int i = 0; i < fileList.size(); i++) {
            UploadFileListReq.UploadFile uploadFile = fileList.get(i);

//            // 从url中获取文件名并下载
//            String fileName = determineFileNameFromHeader(uploadFile.getSourceUrl());
//            if (StringUtils.isEmpty(fileName)) {
//                fileName = extractFileNameFromUrl(uploadFile.getSourceUrl());
//            }
//            uploadFile.setFileName(fileName);

            String fileName = uploadFile.getFileName();
            if (!StringUtils.endsWithIgnoreCase(fileName, ".html")) {
                fileName = fileName + ".html";
                uploadFile.setFileName(fileName);
            }

            try {
                byte[] fileBytes = downloadFileFromUrl(uploadFile.getSourceUrl());
                MultipartFile multipartFile = new MockMultipartFile(
                        "files",
                        fileName,
                        MediaType.TEXT_HTML_VALUE,
                        new ByteArrayInputStream(fileBytes)
                );
                uploadFile.setMultipartFile(multipartFile);
            } catch (IOException ex) {
                log.error(ex.getMessage(), ex);
                throw new ApplicationException(ErrCodeEnum.DOWNLOAD_FROM_URL_ERROR);
            }
        }

        return dealUploadFileListRequest(uploadFileReq);
    }

    private byte[] downloadFileFromUrl(String urlString) throws IOException {
        URL url = new URL(urlString);
        HttpURLConnection connection = (HttpURLConnection) url.openConnection();
        connection.setRequestMethod("GET");

        try (InputStream connInputStream = connection.getInputStream();
             ByteArrayOutputStream byteArrayOutputStream = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[4096];
            int bytesRead;
            while ((bytesRead = connInputStream.read(buffer)) != -1) {
                byteArrayOutputStream.write(buffer, 0, bytesRead);
            }
            return byteArrayOutputStream.toByteArray();
        }
    }

    private String determineFileNameFromHeader(String urlString) {
        try {
            URL url = new URL(urlString);
            HttpURLConnection connection = (HttpURLConnection) url.openConnection();
            connection.setRequestMethod("GET");

            // 获取响应码
            int responseCode = connection.getResponseCode();
            if (responseCode == HttpURLConnection.HTTP_OK) {
                // 获取响应头字段
                Map<String, List<String>> headers = connection.getHeaderFields();
                List<String> contentDisposition = headers.get("Content-Disposition");

                if (contentDisposition != null && !contentDisposition.isEmpty()) {
                    String contentDispositionValue = contentDisposition.get(0);
                    // 查找文件名
                    String fileName = extractFileNameFromContentDisposition(contentDispositionValue);
                    return fileName;
                }
            }
        } catch (IOException ex) {
            log.warn(ex.getMessage(), ex);
        }
        return null;
    }

    private String extractFileNameFromContentDisposition(String contentDisposition) throws UnsupportedEncodingException {
        String fileName = null;
        if (contentDisposition != null && contentDisposition.contains("filename=")) {
            // 解析文件名，支持UTF-8编码的文件名
            String[] parts = contentDisposition.split(";");
            for (String part : parts) {
                if (part.trim().startsWith("filename=")) {
                    String[] nameParts = part.split("=");
                    fileName = nameParts.length > 1 ? nameParts[1].trim().replace("\"", "") : null;
                    // 处理可能存在的URL编码
                    if (fileName != null && fileName.startsWith("=")) {
                        fileName = fileName.substring(1);
                    }
                    fileName = new String(fileName.getBytes("iso-8859-1"), "gb2312");
//                    // 如果文件名包含URL编码的字符，解码它
//                    fileName = URLDecoder.decode(fileName, "utf-8");
                    break;
                }
            }
        }
        return fileName;
    }

    private String extractFileNameFromUrl(String urlString) {
        String[] parts = urlString.split("/");
        return parts[parts.length - 1];
    }

    private List<FileChunkDTO> getChunkByPk(String primitiveName, List<Long> pks) {
        JSONObject respJson = getChunkFromRemoteByPk(primitiveName, pks);
        return buildFileChunkDTO(respJson);
    }

    private JSONObject getChunkFromRemoteByPk(String primitiveName, List<Long> pks) {
        JSONObject query = new JSONObject();
        query.put("index_name", Arrays.asList(primitiveName, "table_chunks_" + primitiveName));
        List<JSONObject> searchCondtions = new ArrayList<>();
        JSONObject condtion = new JSONObject();
        condtion.put("pk", pks);
        searchCondtions.add(condtion);
        query.put("condition_json", searchCondtions);

        String resp = remoteFileUtils.pageListEs(JSONObject.toJSONString(query));
        JSONObject respJson = JSONObject.parseObject(resp);
        if (!Objects.equals(respJson.getInteger("code"), 200))
            throw new ApplicationException(ErrCodeEnum.DOC_CHUNK_ERROR);
        return respJson;
    }

    private void updateChunkField(String primitiveName, List<Long> chunkIds, String colName, Object colValue) {
        JSONObject faqReq = new JSONObject();
        faqReq.put("index_name", primitiveName);
        faqReq.put("pk", chunkIds);
        faqReq.put("col_name", colName);
        faqReq.put("col_value", colValue);

        remoteFileUtils.faqUpdateField(JSONObject.toJSONString(faqReq));
        //更新es中的数据
        String resp = remoteFileUtils.updateFieldteEs(JSONObject.toJSONString(faqReq));
        JSONObject respJson = JSONObject.parseObject(resp);
        if (!Objects.equals(respJson.getInteger("code"), 200))
            throw new ApplicationException(ErrCodeEnum.UPDATE_ES_ERROR);
    }

    @Override
    public Page<KnowledgeBaseFileDTO> folderList(KnowledgeBaseFileQueryReq req) {
        Long kbId = req.getKbId();
        Page<KnowledgeBaseFileDTO> result = new PageDTO<>();
        //找出知识库权限
        Integer basicPermission = knowledgeBaseDomainService.getHighestPermission(kbId);

        Integer fileListType = req.getFileListType();
        List<Integer> statusList = req.getStatusList();
        Integer faqExtractStatus = req.getFaqExtractStatus();
        String fuzzy = req.getFuzzy();
        Long folderId = req.getFolderId();
        Long pageNo = req.getPageNo();
        Long pageSize = req.getPageSize();
        Page<KbFileExt> page = knowledgeBaseListDomainService
                .folderList(kbId, fileListType, statusList, faqExtractStatus, fuzzy, folderId, pageNo, pageSize);

        BeanUtil.copyProperties(page, result);
        result.setRecords(KbFileExtConverter.INSTANCE.kbFileExts2KnowledgeBaseFileDTOS(page.getRecords()));
        buildKbFileListResult(kbId, fileListType, Objects.requireNonNull(result), basicPermission);
        return result;
    }


    @Override
    public LinkedHashSet<KnowledgeBaseFileDTO> fileList(KnowledgeBaseFileQueryReq req) {

        LinkedHashSet<KbFileExt> kbFileExts = Sets.newLinkedHashSet();

        searchFileList(req, kbFileExts);

        return new LinkedHashSet<>(BeanUtil.copyToList(kbFileExts, KnowledgeBaseFileDTO.class));
    }

    @Override
    public LinkedHashSet<KnowledgeBaseFileDTO> flatList(KnowledgeBaseFileQueryReq req) {

        LinkedHashSet<KbFileExt> kbFileExts = Sets.newLinkedHashSet();

        searchUserFileList(req, kbFileExts);

        return new LinkedHashSet<>(KbFileExtConverter.INSTANCE.kbFileExts2KnowledgeBaseFileDTOS(kbFileExts));
    }

    @Override
    public Page<KnowledgeBaseFileDTO> flatFiles(KnowledgeBaseFileQueryReq req) {

        Page<KbFileExt> kbFileExtPage = searchUserOnlyFileList(req);

        Page<KnowledgeBaseFileDTO> result = new Page<>();
        result.setSize(kbFileExtPage.getSize());
        result.setCurrent(kbFileExtPage.getCurrent());
        result.setTotal(kbFileExtPage.getTotal());
        result.setRecords(KbFileExtConverter.INSTANCE.kbFileExts2KnowledgeBaseFileDTOS(kbFileExtPage.getRecords()));

        return result;
    }

    @Override
    public List<KnowledgeBaseFileDTO> onlyFileListByTime(KnowledgeBaseFileQueryReq req) {
        return KbFileExtConverter.INSTANCE.kbFileExts2KnowledgeBaseFileDTOS(knowledgeBaseListDomainService.onlyFileListByTime(req));
    }

    private void searchFileList(KnowledgeBaseFileQueryReq req, LinkedHashSet<KbFileExt> kbFileExts) {
        if (KnowledgeBaseScopeEnums.of(req.getScope()) == KnowledgeBaseScopeEnums.SHARE) {
            //共享知识库查权限
            searchShareFileList(req, kbFileExts);
        }
        if (KnowledgeBaseScopeEnums.of(req.getScope()) == KnowledgeBaseScopeEnums.OWN) {
            //我的知识库查自己上传的文件
            searchUserFileList(req, kbFileExts);
        }

        if (KnowledgeBaseScopeEnums.of(req.getScope()) == KnowledgeBaseScopeEnums.ALL) {
            searchUserFileList(req, kbFileExts);
            searchShareFileList(req, kbFileExts);
        }
    }

    private void searchShareFileList(KnowledgeBaseFileQueryReq req, LinkedHashSet<KbFileExt> kbFileExts) {
        if (!CollectionUtils.isEmpty(req.getKbIds())) {
            for (Long kbId : req.getKbIds()) {
                Boolean permission = privilegeClient.isPermissionApi(PrivilegeTypeEnums.KNOWLEDGE_BASE.getCode(), kbId);
                if (permission) {
                    kbFileExts.addAll(knowledgeBaseListDomainService
                            .fileList(Set.of(kbId), req.getStatus(), req.getKbName(), req.getFolderIds(), null, req.isWithFolder()));
                }
            }
        }
        if (!CollectionUtils.isEmpty(req.getFolderIds())) {
            for (Long folderId : req.getFolderIds()) {
                FolderInfo folderInfo = folderInfoDomainService.findById(folderId);
                if (Objects.nonNull(folderInfo)) {
                    Boolean permission = privilegeClient.isPermissionApi(PrivilegeTypeEnums.KNOWLEDGE_BASE.getCode(), folderInfo.getKbId());
                    if (permission) {
                        kbFileExts.addAll(knowledgeBaseListDomainService
                                .fileList(null, req.getStatus(), req.getKbName(), Set.of(folderId), null, req.isWithFolder()));
                    }
                }


            }

        }

    }

    private void searchUserFileList(KnowledgeBaseFileQueryReq req, LinkedHashSet<KbFileExt> kbFileExts) {
        kbFileExts.addAll(knowledgeBaseListDomainService
                .fileList(req.getKbIds(), req.getStatus(), req.getKbName(), req.getFolderIds(), req.getUserName(), req.isWithFolder()));
    }

    private Page<KbFileExt> searchUserOnlyFileList(KnowledgeBaseFileQueryReq req) {
        return knowledgeBaseListDomainService
                .onlyFileList(req);
    }

    private void buildKbFileListResult(Long kbId, Integer fileListType, Page<KnowledgeBaseFileDTO> result, Integer basicPermission) {
        //查询文件解析/抽取日志
        if (!CollectionUtils.isEmpty(result.getRecords())) {
            if (Objects.isNull(kbId)) {
                kbId = result.getRecords().get(0).getKbId();
            }
            KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
            String primitiveName = knowledgeBase.getPrimitiveName();

            List<Long> fileIds = result.getRecords().stream().map(KnowledgeBaseFileDTO::getId).collect(Collectors.toList());
            if (CollectionUtils.isEmpty(fileIds))
                return;

            //查询解析抽取错误日志
//            List<SynLog> synLogs = synLogDomainService.findByFileIds(fileIds);
//            Map<Long, SynLog> synLogMap = Maps.newHashMap();
//            synLogs.forEach((synLog) -> synLogMap.put(synLog.getTargetId(), synLog));

            //图的点和边的实例数据
            fileIds = result.getRecords().stream().filter(item -> GraphParseStatusEnums.PARSE_SUCCESS.getValue().equals(item.getGraphParseStatus())).map(KnowledgeBaseFileDTO::getId).collect(Collectors.toList());
            Map<Long, GraphInstanceDTO> graphInstanceMap = Maps.newHashMap();
            if (!CollectionUtils.isEmpty(fileIds)) {
                try {
                    graphInstanceMap = graphSearchClient.instance(primitiveName, fileIds);
                } catch (Exception e) {
                    log.error("查询图出现异常:{}", e.getMessage());
                }
            }

            Map<Long, GraphInstanceDTO> finalGraphInstanceMap = graphInstanceMap;


            //处理返回结果
            List<Long> targetIds = result.getRecords().stream().map(KnowledgeBaseFileDTO::getCommonId).toList();
            Map<String, String> idLabelMap = bizLabelDomainService.findLabelMapByTargetIds(targetIds);

            result.getRecords().forEach(kbFile -> {
                //异常日志
                SynLog synLog = synLogDomainService.findByFileId(kbFile.getId());
                if (!Objects.isNull(synLog))
                    kbFile.getSynLogs().add(BeanUtil.copyProperties(synLog, SynLogDTO.class));
                if (FileListTypeEnums.FAQ_LIST.getCode().equals(fileListType) && FaqExtractStatusEnums.EXTRACT_SUCCESS.getValue().equals(kbFile.getFaqExtractStatus())) {
                    Long fileId = kbFile.getId();
                    List<KnowledgeBaseList> faqFiles = knowledgeBaseListDomainService.findFileByFilePaths(kbFile.getKbId(), Arrays.asList(kbFile.getFilePath()), ParseTypeEnums.FAQ_MANAGEMENT.getCode());
                    FaqQueryReq faqQueryReq = FaqQueryReq.builder()
                            .primitiveName(primitiveName)
                            .fileId(fileId)
                            .isNeedFolderId(false)
                            .faqFileIds(CollectionUtils.isEmpty(faqFiles) ? null : faqFiles.stream().map(KnowledgeBaseList::getId).toList()).pageNo(1).pageSize(1).build();
                    kbFile.setAqCount(chunnkDomainService.pageList(faqQueryReq).getTotal());
                } else if (FileListTypeEnums.FILE_LIST.getCode().equals(fileListType) && KbFileStatusEnums.PARSE_SUCCESS.getValue().equals(kbFile.getStatus())) {
                    kbFile.setChunkSize(getFileChunkCount(kbFile.getId()));
                } else if (FileListTypeEnums.GRAPH_LIST.getCode().equals(fileListType) && GraphParseStatusEnums.PARSE_SUCCESS.getValue().equals(kbFile.getGraphParseStatus())) {
                    GraphInstanceDTO graphInstanceDTO = finalGraphInstanceMap.get(kbFile.getId());
                    if (!Objects.isNull(graphInstanceDTO)) {
                        kbFile.setNodeCount(graphInstanceDTO.getNodeCount());
                        kbFile.setEdgeCount(graphInstanceDTO.getEdgeCount());
                    }
                }
                kbFile.setPermission(basicPermission);
                kbFile.setEmbeddingModelName(knowledgeBase.getEmbeddingModelName());
                kbFile.setFileType(StringUtils.isEmpty(kbFile.getChunkType()) ? knowledgeBase.getFileType() : kbFile.getChunkType());
                kbFile.setPdfPage(setPdfPage(kbFile.getConvertedFilePath()));
                //设置文件标签
                setFileLabel(idLabelMap, kbFile);
            });

            //设置文件权限
            setFilesPermission(kbId, basicPermission, result.getRecords(), fileListType);

        }
    }

    private Integer setPdfPage(String filePath) {
        if(StringUtils.isNotBlank(filePath) && filePath.endsWith(".pdf")){
            InputStream inputStream = null;
            try {
                inputStream = fileStorageUtils.getInputStreamByUrl(filePath,null);
                return PdfUtils.getPdfPages(inputStream);
            } catch (Exception e) {
                log.error(e.getMessage());
            }
        }
        return 0;
    }

    private void setFileLabel(Map<String, String> idLabelMap, KnowledgeBaseFileDTO kbFile) {
        String fileLabel = idLabelMap.get(kbFile.getCommonIdStr());
        String label = Stream.of(fileLabel).filter(StringUtils::isNotBlank).collect(Collectors.joining(","));
        kbFile.setLabel(label);
    }

    private void setFileLabel(Map<String, String> idLabelMap, KnowledgeBaseList kbFile) {
        String fileLabel = idLabelMap.get("file_" + kbFile.getId());
        String folderLabel = idLabelMap.get("folder_" + kbFile.getFolderId());
        String label = Stream.of(folderLabel, fileLabel).filter(StringUtils::isNotBlank).collect(Collectors.joining(","));
        kbFile.setLabel(label);
    }

    private void setFilesPermission(Long kbId, Integer basicPermission, List<KnowledgeBaseFileDTO> files, Integer fileListType) {
        //设置文件权限
        if (PermissionEnums.of(basicPermission) != PermissionEnums.ALL) {
            List<KnowledgeBaseList> filesWithPermission;
            if (fileListType.equals(FileListTypeEnums.FAQ_LIST.getCode())) {
                filesWithPermission = knowledgeBaseListDomainService.queryListWithPermission(kbId, FolderTypeEnums.FAQ_EXTRACT.getCode(), ParseTypeEnums.FAQ_PARSE.getCode(), getFaqExtractBizTypes());
            } else {
                filesWithPermission = knowledgeBaseListDomainService.queryListWithPermission(kbId);
            }


            List<KnowledgeBaseFileDTO> fileDTOSWithPermission = CollectionUtils.isEmpty(filesWithPermission) ? Lists.newArrayList() : BeanUtil.copyToList(filesWithPermission, KnowledgeBaseFileDTO.class);
            Map<Long, KnowledgeBaseFileDTO> permissionMap = fileDTOSWithPermission.stream().collect(Collectors.toMap(KnowledgeBaseFileDTO::getCommonId, Function.identity(), (v1, v2) -> v1));

            for (KnowledgeBaseFileDTO kbFile : files) {
                Long fileId = kbFile.getId();
                Long folderId = kbFile.getFolderId();
                KnowledgeBaseFileDTO filePermissionDTO = permissionMap.get(fileId);
                KnowledgeBaseFileDTO folderPermissionDTO = permissionMap.get(folderId);

                int currentPermission = Optional.ofNullable(kbFile.getPermission()).orElse(basicPermission);
                int filePermission = Optional.ofNullable(filePermissionDTO).map(KnowledgeBaseFileDTO::getPermission).orElse(currentPermission);
                int folderPermission = Optional.ofNullable(folderPermissionDTO).map(KnowledgeBaseFileDTO::getPermission).orElse(basicPermission);

                if (Integer.valueOf(1).equals(kbFile.getIsFolder())) {
                    if (folderPermission > currentPermission) {
                        kbFile.setPermission(folderPermission);
                    }
                } else {

                    int finalPermission = NumberUtils.max(basicPermission, folderPermission, filePermission);
                    if (finalPermission > currentPermission) {
                        kbFile.setPermission(finalPermission);
                    }
                }
            }


        }
    }

    private List<Integer> getFaqExtractBizTypes() {
        return List.of(BizTypeEnums.FAQ_EXTRACT_FILE.getCode(), BizTypeEnums.FAQ_EXTRACT_FOLDER.getCode());
    }

    @Override
    public Boolean updateChunk(UpdateChunkReq updateChunkReq) {
        Long kbId = updateChunkReq.getKbId();
        String id = updateChunkReq.getChunkId();
        String content = updateChunkReq.getContent();
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase)) {
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        }
        //查询文本块
        String primitiveName = knowledgeBase.getPrimitiveName();
        JSONObject respJson = this.getChunkFromRemoteByPk(primitiveName, Arrays.asList(Long.parseLong(id)));
        JSONObject data = respJson.getJSONObject("data");
        JSONArray resultData = data.getJSONArray("result_data");
        JSONObject dataJson = (JSONObject) resultData.get(0);
        String indexName = dataJson.getString("_index");
        JSONObject document = dataJson.getJSONObject("_source").getJSONObject("metadata");

        //更新milvus的数据
        JSONObject updateChunk = new JSONObject();
        updateChunk.put("index_name", indexName);
        JSONArray documentlist = new JSONArray();
        document.put("page_content", content);
        documentlist.add(document);
        updateChunk.put("document_list", documentlist);
        remoteFileUtils.faqUpdate(JSONObject.toJSONString(updateChunk));

        //更新es中的数据
        JSONObject updateEsChunk = new JSONObject();
        updateEsChunk.put("index_name", indexName);
        updateEsChunk.put("pk", Arrays.asList(Long.parseLong(id)));
        updateEsChunk.put("col_name", "page_content");
        updateEsChunk.put("col_value", content);
        String resp = remoteFileUtils.updateFieldteEs(JSONObject.toJSONString(updateEsChunk));
        JSONObject result = JSONObject.parseObject(resp);
        if (!Objects.equals(result.getInteger("code"), 200))
            throw new ApplicationException(ErrCodeEnum.UPDATE_ES_ERROR);
        return true;
    }

    @Override
    public Boolean deleteChunk(DeleteChunkReq deleteChunkReq) {
        String tableName = deleteChunkReq.getTableName();
        List<String> chunkIds = deleteChunkReq.getChunkIds();
        //删除向量中的问答对
        JSONObject delParam = new JSONObject();
        delParam.put("collection_name", tableName);
        delParam.put("col_name", "pk");
        delParam.put("col_values", chunkIds.stream().map(Long::parseLong).collect(Collectors.toList()));
        remoteFileUtils.faqDel(JSONObject.toJSONString(delParam));
        //删除es中的问答对
        delParam = new JSONObject();
        delParam.put("index_name", tableName);
        delParam.put("pk_list", chunkIds);
        String resp = remoteFileUtils.faqDelEs(JSONObject.toJSONString(delParam));
        JSONObject respJson = JSONObject.parseObject(resp);
        if (!Objects.equals(respJson.getInteger("code"), 200))
            throw new ApplicationException(ErrCodeEnum.FAQ_DELETE_ERROR);
        return true;
    }

    @Override
    public Boolean reExtractFQA(FilesParseReq filesParseReq) {
        Long kbId = filesParseReq.getKnowledgeBaseId();
        List<FilesParseReq.File> files = filesParseReq.getFiles();
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        //抽取所有
        if (filesParseReq.getIsAll())
            getFilePathByKbId(filesParseReq, Arrays.asList(ParseTypeEnums.FAQ_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode()), null, Arrays.asList(FaqExtractStatusEnums.NO_EXTRACT.getValue(), FaqExtractStatusEnums.EXTRACT_SUCCESS.getValue(), FaqExtractStatusEnums.EXTRACT_FAIL.getValue()));
        else
            getFilePathByFolder(filesParseReq, null, Arrays.asList(FaqExtractStatusEnums.NO_EXTRACT.getValue(), FaqExtractStatusEnums.EXTRACT_SUCCESS.getValue(), FaqExtractStatusEnums.EXTRACT_FAIL.getValue()), null);

        if (CollectionUtils.isEmpty(files))
            return true;

        //删除faq数据
        String primitiveName = knowledgeBase.getPrimitiveName();
        filesParseReq.setKnowledgeBaseName(primitiveName);
        List<Long> fileIds = files.stream().map(FilesParseReq.File::getFileId).toList();
        deleteFAQ(kbId, primitiveName, fileIds);

        //更新文件状态
        FilesParseReq.File file = filesParseReq.getFiles().get(0);
        Long fileId = file.getFileId();
        KnowledgeBaseList kbFile = knowledgeBaseListDomainService.findById(fileId);
        if (Objects.isNull(kbFile))
            throw new ApplicationException(ErrCodeEnum.KB_FILE_NOT_EXISTS_ERROR);
        kbFile.setStatus(KbFileStatusEnums.NORMAL.getValue());
        kbFile.setFaqExtractStatus(FaqExtractStatusEnums.NO_EXTRACT.getValue());
        knowledgeBaseListDomainService.update(kbFile);

        //重新解析抽取
        return doExtractFQA(filesParseReq, true);
    }

    private void deleteFAQ(Long kbId, String primitiveName, List<Long> fileIds) {
        List<KnowledgeBaseList> kbFiles = knowledgeBaseListDomainService.findByIds(fileIds);
        kbFiles.forEach(sourceFile -> {
            Long fileId = sourceFile.getId();
            String filePath = sourceFile.getFilePath();
            List<KnowledgeBaseList> faqFiles = knowledgeBaseListDomainService.findFileByFilePaths(kbId, Arrays.asList(filePath), ParseTypeEnums.FAQ_MANAGEMENT.getCode());
            KnowledgeBaseList faqFile = CollectionUtils.isEmpty(faqFiles) ? null : faqFiles.get(0);
            if (!Objects.isNull(faqFile)) {
                //如果有文件夹
                if (!Objects.isNull(faqFile.getFolderId()) && !Objects.isNull(sourceFile.getFolderId())) {
                    FolderInfo faqFolder = folderDomainService.findById(faqFile.getFolderId());
                    FolderInfo sourceFolder = folderDomainService.findById(sourceFile.getFolderId());
                    if (!Objects.isNull(faqFolder) && !Objects.isNull(sourceFolder)
                            && !Objects.isNull(faqFolder.getFullPath()) && !Objects.isNull(sourceFolder.getFullPath())
                            && StringUtils.equals(faqFolder.getFullPath(), sourceFolder.getFullPath()))
                        //删除faq管理中的faq数据
                        chunnkDomainService.deleteFaq(primitiveName, Arrays.asList(fileId), Arrays.asList(faqFile.getId()));
                } else if (Objects.isNull(faqFile.getFolderId()) && Objects.isNull(sourceFile.getFolderId()))
                    //删除faq管理中的faq数据
                    chunnkDomainService.deleteFaq(primitiveName, Arrays.asList(fileId), Arrays.asList(faqFile.getId()));
            }
        });
    }

    private Boolean doExtractFQA(FilesParseReq filesParseReq, Boolean reExtract) {
        List<FilesParseReq.File> files = filesParseReq.getFiles();
        if (CollectionUtils.isEmpty(files)) {
            return false;
        }

        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(filesParseReq.getKnowledgeBaseId());
        if (Objects.isNull(knowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);

        //解析任务
        List<FileParseTask> taskList = Lists.newArrayList();
        //抽取文件id
        List<Long> extractFileIds = Lists.newArrayList();

        files.forEach(file -> {
            extractFileIds.add(file.getFileId());
            //文件抽取，先解析
            FileParseTaskInfo taskInfo = BeanUtil.copyProperties(filesParseReq, FileParseTaskInfo.class);
            taskInfo.setFiles(Collections.singletonList(BeanUtil.copyProperties(file, FileParseTaskInfo.File.class)));
            taskInfo.setIsExtract(true);
            taskInfo.setParseType(file.getParseType());
            taskInfo.setUserName(UserContext.getUser().getUserName());
            taskInfo.setUserId(UserContext.getUser().getUserId());
            taskInfo.buildKbConf(knowledgeBase.getConfig());
            taskInfo.setIndexName(knowledgeBase.getPrimitiveName());
            taskInfo.setPrimitiveName(knowledgeBase.getPrimitiveName());

            User user = UserContext.getUser();
            String userName = user.getUserName();
            //解析任务
            FileParseTask fileParseTask = new FileParseTask();
            fileParseTask.setKbId(knowledgeBase.getId());
            fileParseTask.setKbName(knowledgeBase.getPrimitiveName());
            fileParseTask.setFileId(file.getFileId());
            fileParseTask.setFileName(file.getFileName());
            fileParseTask.setTaskInfo(JSON.toJSONString(taskInfo));
            fileParseTask.setStatus(ParseTaskStatusEnums.PENDING.getCode());
            fileParseTask.setRetryLimit(retryLimit);
            fileParseTask.setRetryTimes(0);
            fileParseTask.setCreateBy(userName);
            fileParseTask.setModifyBy(userName);
            fileParseTask.setGmtCreate(new Date());
            // fileParseTask.setStartTime(fileParseTask.getGmtCreate());
            fileParseTask.setGmtModified(fileParseTask.getGmtCreate());
            taskList.add(fileParseTask);
        });

        //FAQ抽取，将状态更新为抽取中
        knowledgeBaseListDomainService.updateExtractStatusByIds(extractFileIds, FaqExtractStatusEnums.EXTRACT_ING.getValue());
        //解析文件更新为等待状态
        knowledgeBaseListDomainService.updateParseStatusByIds(extractFileIds, KbFileStatusEnums.PARSE_WAIT.getValue(), true);
        //添加解析任务
        fileParseTaskDomainService.saveBatch(taskList);
        return true;
    }

    @Override
    public Boolean filesAllParse(Long kbId) {
        return filesParseNew(buidParseExtractParam(kbId, Arrays.asList(ParseTypeEnums.FILE_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode())));
    }

    @Override
    public Boolean extractAllFQA(Long kbId) {
        return filesExtractFAQNew(buidParseExtractParam(kbId, Arrays.asList(ParseTypeEnums.FAQ_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode())));
    }

    private FilesParseReq buidParseExtractParam(Long kbId, List<Integer> parseTypes) {
        KnowledgeBase kb = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(kb))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        List<KnowledgeBaseList> kbFiles = knowledgeBaseListDomainService.findNoParseFiles(kbId, parseTypes);
        Map<String, String> idLabelMap = bizLabelDomainService.findLabelByFileIdsAndFolderIds(kbFiles.stream().map(KnowledgeBaseList::getId).toList(), List.of());
        FilesParseReq filesParseReq = new FilesParseReq();
        filesParseReq.setKnowledgeBaseName(kb.getPrimitiveName());
        filesParseReq.setKnowledgeBaseId(kbId);
        filesParseReq.setChunkSize(kb.getChunkSize());
        filesParseReq.setFileType(kb.getFileType());
        filesParseReq.setEmbeddingModelName(kb.getEmbeddingModelName());
        List<FilesParseReq.File> files = Lists.newArrayList();
        kbFiles.forEach(kbFile -> {
            FilesParseReq.File file = new FilesParseReq.File();
            setFileLabel(idLabelMap, kbFile);
            file.setFileId(kbFile.getId());
            file.setFolderId(file.getFolderId());
            file.safeSetLabels(kbFile.getLabel(), ",");
            String fileName = kbFile.getFileName();
            String fileSuffix = fileName.substring(fileName.lastIndexOf(".") + 1);
            String filePath = null;
            if (FILE_TYPE_LIST.contains(fileSuffix))
                filePath = kbFile.getFilePath().replace(storageProperties.getDefaultStorageProperties().getEndPoint() + "/", "");
            else
                filePath = kbFile.getConvertedFilePath().replace(storageProperties.getDefaultStorageProperties().getEndPoint() + "/", "");
            file.setFilePath(filePath);
            file.setFileSize(kbFile.getFileSize() + "MB");
            file.setParentFileName(kbFile.getParentFileName());
            files.add(file);
        });
        filesParseReq.setFiles(files);
        return filesParseReq;
    }

    @Override
    public Boolean graphParse(FilesParseReq filesParseReq) {
        Long kbId = filesParseReq.getKnowledgeBaseId();
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(knowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        getFilePathByFolder(filesParseReq, null, null, Arrays.asList(GraphParseStatusEnums.NORMAL.getValue(), GraphParseStatusEnums.PARSE_SUCCESS.getValue(), GraphParseStatusEnums.PARSE_FAIL.getValue()));

        //解析任务
        List<FileParseTask> taskList = Lists.newArrayList();
        //解析图谱的文件id
        List<Long> graphFileIds = Lists.newArrayList();

        filesParseReq.getFiles().forEach(file -> {

            graphFileIds.add(file.getFileId());
            //文件抽取，先解析
            FileParseTaskInfo taskInfo = BeanUtil.copyProperties(filesParseReq, FileParseTaskInfo.class);
            taskInfo.setFiles(Collections.singletonList(BeanUtil.copyProperties(file, FileParseTaskInfo.File.class)));
            taskInfo.setIsExtract(false);
            taskInfo.setParseType(file.getParseType());
            taskInfo.setUserName(UserContext.getUser().getUserName());
            taskInfo.setUserId(UserContext.getUser().getUserId());
            taskInfo.setIsGraphParse(true);
            taskInfo.buildKbConf(knowledgeBase.getConfig());
            taskInfo.setIndexName(knowledgeBase.getPrimitiveName());
            taskInfo.setPrimitiveName(knowledgeBase.getPrimitiveName());

            User user = UserContext.getUser();
            String userName = user.getUserName();
            //解析任务
            FileParseTask fileParseTask = new FileParseTask();
            fileParseTask.setKbId(knowledgeBase.getId());
            fileParseTask.setKbName(knowledgeBase.getPrimitiveName());
            fileParseTask.setFileId(file.getFileId());
            fileParseTask.setFileName(file.getFileName());
            fileParseTask.setTaskInfo(JSON.toJSONString(taskInfo));
            fileParseTask.setStatus(ParseTaskStatusEnums.PENDING.getCode());
            fileParseTask.setRetryLimit(retryLimit);
            fileParseTask.setRetryTimes(0);
            fileParseTask.setCreateBy(userName);
            fileParseTask.setModifyBy(userName);
            fileParseTask.setGmtCreate(new Date());
            // fileParseTask.setStartTime(fileParseTask.getGmtCreate());
            fileParseTask.setGmtModified(fileParseTask.getGmtCreate());
            taskList.add(fileParseTask);
        });

        //图谱抽取，将状态更新为抽取中
        knowledgeBaseListDomainService.updateGraphExtractByIds(graphFileIds, GraphParseStatusEnums.PARSE_ING.getValue());
        //解析文件更新为等待状态
        knowledgeBaseListDomainService.updateParseStatusByIds(graphFileIds, KbFileStatusEnums.PARSE_WAIT.getValue(), true);
        //添加解析任务
        fileParseTaskDomainService.saveBatch(taskList);
        return true;
    }

    @Override
    public Integer getGraphParseStatus(Long fileId) {
        if (Objects.isNull(fileId)) {
            return null;
        }
        KnowledgeBaseList knowledgeBaseFile = knowledgeBaseListDomainService.findById(fileId);
        return Objects.isNull(knowledgeBaseFile) ? null : knowledgeBaseFile.getGraphParseStatus();
    }

    @Override
    public void viewFile(HttpServletResponse response, String fileUrl) throws IOException {
        String mimeType = "text/csv";
        int lastIndex = fileUrl.lastIndexOf(".");
        String ext = fileUrl.substring(lastIndex + 1);
        if ("csv".equalsIgnoreCase(ext)) {
            mimeType = "text/csv";
        } else if ("pdf".equalsIgnoreCase(ext)) {
            mimeType = "application/pdf";
        } else if ("txt".equalsIgnoreCase(ext)) {
            mimeType = "text/plain";
        } else if ("doc".equalsIgnoreCase(ext)) {
            mimeType = "application/msword";
        } else if ("docx".equalsIgnoreCase(ext)) {
            mimeType = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
        } else if ("xls".equalsIgnoreCase(ext)) {
            mimeType = "application/vnd.ms-excel";
        } else if ("xlsx".equalsIgnoreCase(ext)) {
            mimeType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
        } else if ("bmp".equalsIgnoreCase(ext)) {
            mimeType = "image/bmp";
        } else if ("gif".equalsIgnoreCase(ext)) {
            mimeType = "image/gif";
        } else if ("jpeg".equalsIgnoreCase(ext) || "jpg".equalsIgnoreCase(ext)) {
            mimeType = "image/jpeg";
        } else if ("webp".equalsIgnoreCase(ext)) {
            mimeType = "image/webp";
        } else if ("png".equalsIgnoreCase(ext)) {
            mimeType = "image/png";
        }
        Resource resource = new UrlResource(fileUrl);
        InputStream inputStream = resource.getInputStream();
        response.setContentType(mimeType);
        getFileSample(inputStream, response.getOutputStream(), 100);
    }

    private void getFileSample(InputStream source, OutputStream target, int size) throws IOException {
        try {
            BufferedReader reader = new BufferedReader(new InputStreamReader(source));
            BufferedWriter writer = new BufferedWriter(new OutputStreamWriter(target));

            String line;
            int count = 0;
            while ((line = reader.readLine()) != null && count < size) {
                writer.write(line);
                writer.newLine();
                count++;
            }

            writer.flush();

            reader.close();
            writer.close();
        } catch (IOException e) {

        }
    }

    @Override
    public List<KnowledgeBaseFileDTO> queryList(Long kbId, List<Integer> types) {
        Integer basicPermission = knowledgeBaseDomainService.getHighestPermission(kbId);
        List<KnowledgeBaseList> knowledgeBaseLists = knowledgeBaseListDomainService.queryList(kbId, types);
        List<KnowledgeBaseFileDTO> knowledgeBaseFileDTOS = CollectionUtils.isEmpty(knowledgeBaseLists) ? Lists.newArrayList() : BeanUtil.copyToList(knowledgeBaseLists, KnowledgeBaseFileDTO.class);
        setFilesPermission(kbId, basicPermission, knowledgeBaseFileDTOS, FileListTypeEnums.FILE_LIST.getCode());
        return knowledgeBaseFileDTOS;
    }

    @Override
    public Object docUploadFile(String sessionId, List<String> uids, MultipartFile[] files) {
        //通过sessionid查询助多模态模型
        String multiModelName = searchConfigClient.selectMultiModelName(sessionId);
        //创建知识库
        String kbName = sessionId;
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbName(kbName, null);
        Long kbId = Objects.isNull(knowledgeBase) ? null : knowledgeBase.getId();
        if (Objects.isNull(knowledgeBase)) {
            KnowledgeBaseCreateReq knowledgeBaseCreateReq = new KnowledgeBaseCreateReq();
            knowledgeBaseCreateReq.setFileType("intelligent");
            knowledgeBaseCreateReq.setKbName(kbName);
            knowledgeBaseCreateReq.setKbType(KbTypeEnums.DOC_QA.getCode());
            knowledgeBaseCreateReq.setPlatform(PlatFormEnums.RAG_QA.getCode());
            knowledgeBaseCreateReq.setMultiModelName(multiModelName);
            KnowledgeBaseDTO kb = knowledgeBaseDomainService.createKb(knowledgeBaseCreateReq);
            kbId = kb.getId();
        }

        //文件上传
        UploadFileListReq uploadFileListReq = new UploadFileListReq();
        uploadFileListReq.setIsExtract(false);
        uploadFileListReq.setIsParse(true);
        uploadFileListReq.setKbId(kbId);
        uploadFileListReq.setSaveTxt(true);
        uploadFileListReq.setChunking(false);
        uploadFileListReq.setFileListType(ParseTypeEnums.DOC_QA.getCode());
        List<UploadFileListReq.UploadFile> fileList = Lists.newArrayList();
        uploadFileListReq.setFileList(fileList);
        for (int i = 0; i < files.length; i++) {
            MultipartFile file = files[i];
            String fileName = file.getOriginalFilename();
            if (UrlKeywordChecker.containsUrlKeywords(fileName))
                throw new ApplicationException(ErrCodeEnum.FILE_NAME_ILLEGAL.getErrCode(), "【" + fileName + "】" + ErrCodeEnum.FILE_NAME_ILLEGAL.getErrMsg());
            UploadFileListReq.UploadFile uploadFile = new UploadFileListReq.UploadFile();
            uploadFile.setFileName(fileName);
            uploadFile.setUid(uids.get(i));
            uploadFile.setMultipartFile(files[i]);
            uploadFile.setChunking(false);
            fileList.add(uploadFile);
        }
        return docUploadFile(uploadFileListReq);
    }

    private Object docUploadFile(UploadFileListReq uploadFileReq) {

        List<UploadFileListReq.UploadFile> fileList = uploadFileReq.getFileList();
        //校验文件列表是否有同名文件  返回异常:上传文件列表存在同名文件，请重新上传
        if (knowledgeBaseListDomainService.checkFileName(fileList))
            throw new ApplicationException(ErrCodeEnum.FILE_NAME_SAME_ERROR);

        Long kbId = uploadFileReq.getKbId();
        KnowledgeBase dbKnowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(dbKnowledgeBase))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        uploadFileReq.setPrimitiveName(dbKnowledgeBase.getRealPrimitiveName());
        uploadFileReq.setPlatform(dbKnowledgeBase.getPlatform());

        Set<String> existedFiles = Sets.newHashSet();
        List<KbFile> uploadKbFiles = Lists.newArrayList();
        Set<String> uploadingFiles = Sets.newHashSet();

        //文件上传
        dealNormalFiles(uploadFileReq, dbKnowledgeBase, existedFiles, uploadKbFiles, uploadingFiles);

        //入库 解析
        List<KnowledgeBaseFileDTO> kbFileDTOs = Lists.newArrayList();
        if (!CollectionUtils.isEmpty(fileList)) {
            Boolean saveTxt = uploadFileReq.getSaveTxt();
            String platform = uploadFileReq.getPlatform();
            boolean chunking = uploadFileReq.isChunking();
            String primitiveName = dbKnowledgeBase.getPrimitiveName();
            Integer parseType = ParseTypeEnums.DOC_QA.getCode();
            List<Integer> parseTypes = Lists.newArrayList(ParseTypeEnums.FAQ_PARSE.getCode());
            List<KnowledgeBaseFileDTO> knowledgeBaseList = addKnowledgeBaseList(kbId, dbKnowledgeBase.getSourceUrl(), uploadKbFiles, parseType, parseTypes, chunking);
            FilesParseReq filesParseReq = buildFilesParseParam(knowledgeBaseList, kbId, primitiveName, chunking);
            List<FilesParseReq.File> files = filesParseReq.getFiles();
            KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
            if (Objects.isNull(knowledgeBase))
                throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
            //发送消息
            for (FilesParseReq.File file : files) {
                FileParseTaskInfo taskInfo = BeanUtil.copyProperties(filesParseReq, FileParseTaskInfo.class);
                taskInfo.setFiles(Collections.singletonList(BeanUtil.copyProperties(file, FileParseTaskInfo.File.class)));
                taskInfo.setUserName(UserContext.getUser().getUserName());
                taskInfo.setUserId(UserContext.getUser().getUserId());
                taskInfo.setApiKey(UserContext.getUser().getApiKey());
                taskInfo.buildKbConf(knowledgeBase.getConfig());
                taskInfo.setIndexName(primitiveName);
                taskInfo.setSaveTxt(saveTxt);
                taskInfo.setNeedChunk(chunking);
                taskInfo.adjustByPlatform(platform, chunking);
                taskInfo.setParseType(parseType);
                knowledgeBaseListDomainService.updateStatusByIds(Lists.newArrayList(file.getFileId()), KbFileStatusEnums.PARSE_ING.getValue(), false);
                rocketMQTemplate.syncSend(MessageChannel.KB_FILE_PARSE_TOPIC, MessageBuilder.withPayload(taskInfo).build());
                ObjectMapper objectMapper = new ObjectMapper();
                try {
                    log.info("kb-file-parse-extract-topic-message:{}", objectMapper.writeValueAsString(taskInfo));
                } catch (JsonProcessingException e) {
                    log.error(e.getMessage(), e);
                    throw new RuntimeException(e);
                }
            }
            return knowledgeBaseList;
        }

        return kbFileDTOs;
    }

    @Override
    public List<KnowledgeBaseFileDTO> getByKbNameAndUid(String kbName, List<String> fileUids) {
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByKbName(kbName, null);
        if (Objects.isNull(knowledgeBase))
            return null;
        //持久化文件
        knowledgeBaseListDomainService.updateTempStatusByUid(fileUids, TempStatusEnums.PERSISTENCE.getCode());
        List<KnowledgeBaseList> knowledgeBaseLists = knowledgeBaseListDomainService.getByKbIdAndUid(knowledgeBase.getId(), null, TempStatusEnums.PERSISTENCE.getCode());
        return BeanUtil.copyToList(knowledgeBaseLists, KnowledgeBaseFileDTO.class);
    }

    @Override
    public List<FileStatusDTO> getFileStatusByUids(List<String> uids) {
        if (CollectionUtils.isEmpty(uids))
            return null;
        List<KnowledgeBaseList> knowledgeBaseLists = knowledgeBaseListDomainService.findByUids(uids);
        return CollectionUtils.isEmpty(knowledgeBaseLists) ? null : BeanUtil.copyToList(knowledgeBaseLists, FileStatusDTO.class);
    }

    @Override
    public List<KnowledgeBaseFileDTO> queryListWithPermission(Long kbId) {
        List<KnowledgeBaseList> knowledgeBaseLists = knowledgeBaseListDomainService.queryListWithPermission(kbId);
        return CollectionUtils.isEmpty(knowledgeBaseLists) ? Lists.newArrayList() : BeanUtil.copyToList(knowledgeBaseLists, KnowledgeBaseFileDTO.class);
    }

    @Override
    public String queryCreator(Long id) {
        return knowledgeBaseListDomainService.queryCreator(id);
    }

    @Override
    public Boolean exist(String kbName, String fileName, Integer type) {
        KnowledgeBase knowledgeBase = knowledgeBaseDomainService.findByPrimitiveName(kbName, null);
        if (Objects.isNull(knowledgeBase))
            return false;
        return !Objects.isNull(knowledgeBaseListDomainService.findFile(knowledgeBase.getId(), fileName, type));
    }

    @Override
    public Boolean createCollect(CreateCollectReq createCollectReq) {
        List<Long> fileIds = createCollectReq.getFileIds();
        List<String> groupIds = createCollectReq.getGroupIds();
        Long kbId = createCollectReq.getKbId();
        Integer fileListType = createCollectReq.getFileListType();

        if (CollectionUtils.isEmpty(fileIds) && CollectionUtils.isEmpty(groupIds))
            throw new ApplicationException(ErrCodeEnum.FILE_OR_GROUP_NOT_NULL);

        String fileName = null;
        if (!CollectionUtils.isEmpty(fileIds)) {
            KnowledgeBaseList kbFile = knowledgeBaseListDomainService.findById(fileIds.get(0));
            fileName = kbFile.getFileName();
        }

        List<KnowledgeBaseList> kbFiles = Lists.newArrayList();
        if (!CollectionUtils.isEmpty(groupIds)) {
            List<Integer> parseTypes = Lists.newArrayList();
            if (Objects.equals(FileListTypeEnums.FILE_LIST.getCode(), fileListType))
                parseTypes = Arrays.asList(ParseTypeEnums.FILE_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode());
            else if (Objects.equals(FileListTypeEnums.FAQ_LIST.getCode(), fileListType))
                parseTypes = Arrays.asList(ParseTypeEnums.FAQ_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode());
            kbFiles = knowledgeBaseListDomainService.findByKbIdAndGroupIds(kbId, groupIds, parseTypes);
        }

        if (CollectionUtils.isEmpty(fileIds) && !CollectionUtils.isEmpty(groupIds) && !CollectionUtils.isEmpty(kbFiles)) {
            fileName = kbFiles.get(0).getParentFileName();
        }

        if (CollectionUtils.isEmpty(fileIds))
            fileIds = Lists.newArrayList();

        if (!CollectionUtils.isEmpty(kbFiles))
            fileIds.addAll(kbFiles.stream().map(KnowledgeBaseList::getId).collect(Collectors.toList()));

        //更新
        String groupName = fileName;
        Integer groupId = groupName.hashCode() & Integer.MAX_VALUE;
        return knowledgeBaseListDomainService.updateMultiversion(fileIds, groupName, String.valueOf(groupId), null);
    }

    @Override
    public Boolean remove(RemoveCollectReq removeCollectReq) {
        Long kbId = removeCollectReq.getKbId();
        List<Long> fileIds = removeCollectReq.getFileIds();
        if (CollectionUtils.isEmpty(fileIds))
            return false;

        List<KnowledgeBaseList> kbFiles = knowledgeBaseListDomainService.findByIds(fileIds);
        kbFiles.forEach(kbFile -> {
            String fileName = kbFile.getFileName();
            String parentFileName = kbFile.getParentFileName();
            if (Objects.equals(fileName, parentFileName))
                fileName = System.currentTimeMillis() + fileName;
            knowledgeBaseListDomainService.updateMultiversion(Arrays.asList(kbFile.getId()), fileName, (fileName.hashCode() & Integer.MAX_VALUE) + "", null);
        });
        return true;
    }

    @Override
    public Boolean transfer(FileCollectTransferReq fileCollectTransferReq) {
        Long kbId = fileCollectTransferReq.getKbId();
        List<String> srcGroupIds = fileCollectTransferReq.getSrcGroupIds();
        Integer fileListType = fileCollectTransferReq.getFileListType();
        List<Long> fileIds = fileCollectTransferReq.getFileIds();
        if (CollectionUtils.isEmpty(fileIds))
            fileIds = Lists.newArrayList();
        if (!CollectionUtils.isEmpty(srcGroupIds)) {
            List<Integer> parseTypes = Lists.newArrayList();
            if (Objects.equals(FileListTypeEnums.FILE_LIST.getCode(), fileListType))
                parseTypes = Arrays.asList(ParseTypeEnums.FILE_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode());
            else if (Objects.equals(FileListTypeEnums.FAQ_LIST.getCode(), fileListType))
                parseTypes = Arrays.asList(ParseTypeEnums.FAQ_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode());
            List<KnowledgeBaseList> kbFiles = knowledgeBaseListDomainService.findByKbIdAndGroupIds(kbId, srcGroupIds, parseTypes);
            if (!CollectionUtils.isEmpty(kbFiles))
                fileIds.addAll(kbFiles.stream().map(KnowledgeBaseList::getId).collect(Collectors.toList()));
        }
        String parentFileName = fileCollectTransferReq.getParentFileName();
        String groupId = fileCollectTransferReq.getGroupId();
        List<KnowledgeBaseList> kbFiles = knowledgeBaseListDomainService.findByIds(fileIds);
        kbFiles.forEach(kbFile -> knowledgeBaseListDomainService
                .updateMultiversion(Arrays.asList(kbFile.getId()), parentFileName, groupId, null));
        return true;
    }

    @Override
    public Boolean dissolve(DissolveCollectReq dissolveCollectReq) {
        Long kbId = dissolveCollectReq.getKbId();
        List<String> groupIds = dissolveCollectReq.getGroupIds();
        Integer fileListType = dissolveCollectReq.getFileListType();
        List<Integer> parseTypes = Lists.newArrayList();
        if (Objects.equals(FileListTypeEnums.FILE_LIST.getCode(), fileListType))
            parseTypes = Arrays.asList(ParseTypeEnums.FILE_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode());
        else if (Objects.equals(FileListTypeEnums.FAQ_LIST.getCode(), fileListType))
            parseTypes = Arrays.asList(ParseTypeEnums.FAQ_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode());

        KnowledgeBase kb = knowledgeBaseDomainService.findByKbId(kbId);
        if (Objects.isNull(kb))
            throw new ApplicationException(ErrCodeEnum.KB_NOT_EXISTS_ERROR);
        List<KnowledgeBaseList> kbFiles = knowledgeBaseListDomainService.findByKbIdAndGroupIds(kbId, groupIds, parseTypes);
        kbFiles.forEach(kbFile -> knowledgeBaseListDomainService.updateMultiversion(Arrays.asList(kbFile.getId()), kbFile.getFileName(), (kbFile.getFileName().hashCode() & Integer.MAX_VALUE) + "", null));
        return true;
    }

    @Override
    public List<CollectDTO> collectList(Long kbId, Integer fileListType) {

        List<KnowledgeBaseList> kbFiles = knowledgeBaseListDomainService.collectList(kbId, fileListType);

        return BeanUtil.copyToList(kbFiles, CollectDTO.class);
    }

    @Override
    public List<KnowledgeBaseFileDTO> getByGroupId(Long kbId, String groupId, Integer fileListType) {
        List<Integer> parseTypes = Lists.newArrayList();
        if (Objects.equals(FileListTypeEnums.FILE_LIST.getCode(), fileListType))
            parseTypes = Arrays.asList(ParseTypeEnums.FILE_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode());
        else if (Objects.equals(FileListTypeEnums.FAQ_LIST.getCode(), fileListType))
            parseTypes = Arrays.asList(ParseTypeEnums.FAQ_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode());
        List<KnowledgeBaseList> kbFiles = knowledgeBaseListDomainService.findByKbIdAndGroupIds(kbId, Arrays.asList(groupId), parseTypes);
        return CollectionUtils.isEmpty(kbFiles) ? null : BeanUtil.copyToList(kbFiles, KnowledgeBaseFileDTO.class);
    }

    @Override
    public List<KnowledgeBaseFileDTO> scatterList(Long kbId, Integer fileListType) {
        List<KnowledgeBaseList> knowledgeBaseLists = knowledgeBaseListDomainService.scatterList(kbId, fileListType);
        if (!CollectionUtils.isEmpty(knowledgeBaseLists)) {
            List<Long> fileIds = knowledgeBaseLists.stream().map(KnowledgeBaseList::getId).collect(Collectors.toList());
            knowledgeBaseLists = knowledgeBaseListDomainService.findByIds(fileIds);
            return CollectionUtils.isEmpty(knowledgeBaseLists) ? null : BeanUtil.copyToList(knowledgeBaseLists, KnowledgeBaseFileDTO.class);
        }
        return null;
    }

    @Override
    public Boolean addLabel(Long fileId, String label) {
        KnowledgeBaseList kbFile = knowledgeBaseListDomainService.findById(fileId);
        if (Objects.isNull(kbFile))
            throw new ApplicationException(ErrCodeEnum.KB_FILE_NOT_EXISTS_ERROR);
        kbFile.setFileLabel(label);
        knowledgeBaseListDomainService.update(kbFile);
        kbLabelHisDomainService.addLabelsHis(kbFile.getKbId(), label);
        return true;
    }

    @Override
    public List<KnowledgeBaseFileDTO> deleteByUid(String queryId, String fileUid) {
        List<KnowledgeBaseList> kbFiles = knowledgeBaseListDomainService.findByUids(Arrays.asList(fileUid));
        if (CollectionUtils.isEmpty(kbFiles))
            throw new ApplicationException(ErrCodeEnum.KB_FILE_NOT_EXISTS_ERROR);
        KnowledgeBaseList knowledgeBaseList = kbFiles.get(0);
        deleteById(knowledgeBaseList.getId());
        Long kbId = knowledgeBaseList.getKbId();
        List<KnowledgeBaseList> files = knowledgeBaseListDomainService.findFileByKbId(kbId, Arrays.asList(ParseTypeEnums.DOC_QA.getCode()));
        List<KnowledgeBaseFileDTO> fileDTOS = CollectionUtils.isEmpty(files) ? Lists.newArrayList() : BeanUtil.copyToList(files, KnowledgeBaseFileDTO.class);
        //修改文档上传对话中的文件引用
        List<FilePathDTO> filePathDTOS = convertToFilePathDTOS(fileDTOS);
        dialoguaClient.updateQaFiles(queryId, JSON.toJSONString(filePathDTOS));
        return fileDTOS;
    }

    private List<FilePathDTO> convertToFilePathDTOS(List<KnowledgeBaseFileDTO> files) {
        if (CollectionUtils.isEmpty(files))
            return null;
        List<FilePathDTO> filePathDTOS = Lists.newArrayList();
        files.forEach(file -> {
            String parsedFilePath;
            FilePathDTO filePathDTO = new FilePathDTO();
            String filePath = file.getConvertedFilePath();
            String fileName;
            if (IndexConstant.IMAGE_TYPE_LIST.contains(file.getFileName().substring(file.getFileName().lastIndexOf(".") + 1)))
                parsedFilePath = file.getFilePath();
            else if (filePath.endsWith(".md")) {
                fileName = file.getFileName();
                filePath = file.getFilePath();
                String filePrefix = filePath.substring(0, filePath.lastIndexOf("/"));
                parsedFilePath = filePrefix + "/parsed/" + fileName + ".txt";
            } else {
                fileName = filePath.substring(filePath.lastIndexOf("/") + 1);
                filePath = file.getFilePath();
                String filePrefix = filePath.substring(0, filePath.lastIndexOf("/"));
                parsedFilePath = filePrefix + "/parsed/" + fileName + ".txt";
            }

            filePathDTO.setFilePath(file.getFilePath());
            filePathDTO.setConvertedFilePath(parsedFilePath);
            filePathDTO.setName(file.getFileName());
            filePathDTO.setUid(file.getUid());
            filePathDTO.setSize(file.getFileSize() + "MB");
            filePathDTOS.add(filePathDTO);
        });
        return filePathDTOS;
    }

    @Override
    public List<FileChunkDTO> getKbFileChunks(String kbName, String fileName, Integer pageNo, Integer pageSize) {
        JSONObject respJson = chunnkDomainService.getChunks(kbName, fileName, pageNo, pageSize);
        return buildFileChunkDTO(respJson);
    }

    private List<FileChunkDTO> buildFileChunkDTO(JSONObject respJson) {
        if (Objects.isNull(respJson))
            return com.google.common.collect.Lists.newArrayList();
        JSONObject data = respJson.getJSONObject("data");
        List<FileChunkDTO> chunks = com.google.common.collect.Lists.newArrayList();
        if (Objects.isNull(data)) {
            return chunks;
        }
        JSONArray resultData = data.getJSONArray("result_data");
        if (Objects.isNull(resultData)) {
            return chunks;
        }
        resultData.forEach(result -> {
            FileChunkDTO fileChunkDTO = new FileChunkDTO();
            Long chunkId = ((JSONObject) result).getLong("_id");
            String tableName = ((JSONObject) result).getString("_index");
            JSONObject dataJson = ((JSONObject) result).getJSONObject("_source");
            String chunkContent = dataJson.getString("page_content");
            JSONObject chunkMetadataJson = dataJson.getJSONObject("metadata");
            fileChunkDTO.setPicChunkIdList(JSON.parseArray(chunkMetadataJson.getString("pic_children_id_list"), Long.class));
            fileChunkDTO.setPicUrlList(JSON.parseArray(chunkMetadataJson.getString("pic_url_list"), String.class));
            fileChunkDTO.setImagePath(chunkMetadataJson.getString("image_path"));
            fileChunkDTO.setPageNumbers(chunkMetadataJson.getJSONArray("page_number"));
            fileChunkDTO.setPositions(chunkMetadataJson.getJSONArray("position"));
            fileChunkDTO.setPageSizes(chunkMetadataJson.getJSONArray("page_size"));
            fileChunkDTO.setOffsets(chunkMetadataJson.getJSONArray("offset"));
            fileChunkDTO.setTable(chunkMetadataJson.getString("table_name"));
            fileChunkDTO.setType(chunkMetadataJson.getString("type"));
            fileChunkDTO.setTableName(tableName);
            if (org.apache.commons.lang3.StringUtils.isNotBlank(chunkContent)) {
                fileChunkDTO.setId(chunkId);
                fileChunkDTO.setContent(chunkContent);
                chunks.add(fileChunkDTO);
            }
        });
        return chunks;
    }


    @Override
    public InputStream pageFileStream(PageFileStreamReq pageFileStreamReq, HttpHeaders httpHeaders) throws IOException, FileStorageException {
        if (Objects.isNull(pageFileStreamReq.getPageNo()) || Objects.isNull(pageFileStreamReq.getPageSize())) {
            return fileStorageUtils.getInputStreamByUrl(pageFileStreamReq.getConvertedFilePath(), null);
        } else {
            if (!checkFileExtIsSupported(pageFileStreamReq)) {
                throw new ApplicationException(ErrCodeEnum.PARAM_ILLEGAL);
            }
            return fileProcessorContext.pageInputStream(pageFileStreamReq, httpHeaders);
        }
    }

    @Override
    public JSONPagination.PageResult<JsonNode> pageFile(PageFileStreamReq pageFileStreamReq, HttpHeaders headers) throws IOException, FileStorageException {
        InputStream inputStreamByUrl = fileStorageUtils.getInputStreamByUrl(pageFileStreamReq.getConvertedFilePath(), null);
        return JSONPagination.paginateStream(inputStreamByUrl, pageFileStreamReq.getPageNo(), pageFileStreamReq.getPageSize());
    }

    @Override
    public Integer totalPages(Long fileId) {
        KnowledgeBaseList file = knowledgeBaseListDomainService.findById(fileId);
        if (Objects.nonNull(file) && StringUtils.isNotBlank(file.getConvertedFilePath())) {
            return fileProcessorContext.totalPages(file.getConvertedFilePath());
        }
        return 0;
    }

    @Override
    public Long getSequenceCodeByFileId(Long fileId) {
        if (Objects.isNull(fileId) || fileId < 0) {
            throw new ApplicationException(ErrCodeEnum.DOC_ID_PARAM_ERROR);
        }
        return fileParseTaskDomainService.getSequenceByFileId(fileId);
    }

    private boolean checkFileExtIsSupported(PageFileStreamReq pageFileStreamReq) {
        String ext = FileUtils.getExt(pageFileStreamReq.getConvertedFilePath());
        log.info("file ext:{}", ext);
        if ("md".equals(ext) || "pdf".equals(ext)) {
            Tika tika = new Tika();
            byte[] mediaTypeByteArrayByUrl = fileStorageUtils.getMediaTypeByteArrayByUrl(pageFileStreamReq.getConvertedFilePath(), null);
            String detect = tika.detect(mediaTypeByteArrayByUrl);
            log.info("tika detect:{}", detect);
            return MediaType.APPLICATION_PDF_VALUE.equals(detect) || MediaType.TEXT_PLAIN_VALUE.equals(detect) || MediaType.APPLICATION_OCTET_STREAM_VALUE.equals(detect);
        }
        return false;

    }

}
