package com.gientech.ragindexservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.plugins.pagination.PageDTO;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.index.dto.KnowledgeBaseFileDTO;
import com.gientech.ragcommon.index.enmus.*;
import com.gientech.ragcommon.index.request.FolderAndFilerReq;
import com.gientech.ragindexservice.domain.entity.KbFileExt;
import com.gientech.ragindexservice.domain.entity.KnowledgeBaseFile;
import com.gientech.ragindexservice.domain.entity.KnowledgeBaseList;
import com.gientech.ragindexservice.domain.mapper.KnowledgeBaseListMapper;
import com.gientech.ragindexservice.domain.model.KnowledgeBaseFileDO;
import com.gientech.ragindexservice.domain.model.KnowledgeBaseListDO;
import com.gientech.ragindexservice.domain.repository.KnowledgeBaseListRepository;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import org.springframework.util.CollectionUtils;

import java.time.LocalDateTime;
import java.util.*;

@Repository
public class KnowledgeBaseListRepositoryImpl extends ServiceImpl<KnowledgeBaseListMapper, KnowledgeBaseListDO> implements KnowledgeBaseListRepository {

    @Autowired
    private KnowledgeBaseListMapper knowledgeBaseListMapper;

    @Override
    public List<KnowledgeBaseList> insertBatch(List<KnowledgeBaseList> knowledgeBaseLists) {
        if (CollectionUtils.isEmpty(knowledgeBaseLists)) {
            return Lists.newArrayList();
        }
        User user = UserContext.getUser();
        String userName = user.getUserName();
        knowledgeBaseLists.forEach(item -> {
            item.setStatus(Objects.isNull(item.getStatus()) ? KbFileStatusEnums.NORMAL.getValue() : item.getStatus());
            item.setFaqExtractStatus(Objects.isNull(item.getFaqExtractStatus()) ? FaqExtractStatusEnums.NO_EXTRACT.getValue() : item.getFaqExtractStatus());
            item.setGraphParseStatus(Objects.isNull(item.getGraphParseStatus()) ? GraphParseStatusEnums.NORMAL.getValue() : item.getGraphParseStatus());
            item.setCreateBy(userName);
            item.setGmtCreate(new Date());
            item.setModifyBy(userName);
            item.setGmtModified(item.getGmtCreate());
        });
        List<KnowledgeBaseListDO> knowledgeBaseListDOS = BeanUtil.copyToList(knowledgeBaseLists, KnowledgeBaseListDO.class);
        knowledgeBaseListMapper.saveBatch(knowledgeBaseListDOS);
        return BeanUtil.copyToList(knowledgeBaseListDOS, KnowledgeBaseList.class);
    }

    @Override
    public void updateStatusByFilePaths(List<String> filePaths, Integer status) {
        if (CollectionUtils.isEmpty(filePaths)) {
            return;
        }
        knowledgeBaseListMapper.updateStatusByFilePaths(filePaths, status);
    }

    @Override
    public void updateLabels(List<Long> fileIds, String label) {
        if (CollectionUtils.isEmpty(fileIds)) {
            return;
        }
        //knowledgeBaseListMapper.updateLabels(fileIds, label);
    }

    @Override
    public void updateStatusByIds(List<Long> ids, Integer status, boolean convertedFilePathSetNull) {
        if (CollectionUtils.isEmpty(ids)) {
            return;
        }
        knowledgeBaseListMapper.updateStatusByIds(ids, status, convertedFilePathSetNull);
    }

    @Override
    public void updateParseStatusByIds(List<Long> fileIds, Integer status, Boolean needUpdateTime) {
        if (CollectionUtils.isEmpty(fileIds)) {
            return;
        }
        knowledgeBaseListMapper.updateParseStatusByIds(fileIds, status, needUpdateTime);
    }

    @Override
    public void updateGraphExtractByIds(List<Long> ids, Integer graphExtractStatus) {
        if (CollectionUtils.isEmpty(ids)) {
            return;
        }
        knowledgeBaseListMapper.updateGraphExtractByIds(ids, graphExtractStatus);
    }

    @Override
    public Page<KnowledgeBaseList> list(Long kbId, Integer fileListType, String fuzzy, Integer status, Integer faqExtractStatus, String parentFileName, Long pageNo, Long pageSize) {
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper
                .eq("kb_id", kbId)
                .ne("status", KbFileStatusEnums.DELETE.getValue())
                .eq(!Objects.isNull(status), "status", status)
                .eq(!Objects.isNull(faqExtractStatus), "faq_extract_status", faqExtractStatus)
                .eq(!Objects.isNull(parentFileName), "parent_file_name", parentFileName);

        if (FileListTypeEnums.FILE_LIST.getCode().equals(fileListType))
            queryWrapper.in("parse_type", Arrays.asList(ParseTypeEnums.FILE_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode()));
        else if (FileListTypeEnums.FAQ_LIST.getCode().equals(fileListType))
            queryWrapper.in("parse_type", Arrays.asList(ParseTypeEnums.FAQ_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode()));
        else if (FileListTypeEnums.GRAPH_LIST.getCode().equals(fileListType))
            queryWrapper.in("parse_type", Arrays.asList(ParseTypeEnums.GRAPH_PARSE.getCode()));

        if (StringUtils.isNotBlank(fuzzy))
            queryWrapper.and(name -> name
                    .like("file_name", fuzzy)
                    .or(id -> id.like("id", fuzzy))
                    .or(parentName -> parentName.like("parent_file_name", fuzzy)));

        queryWrapper.orderByDesc("id");
        Page<KnowledgeBaseListDO> page = new Page<>(pageNo, pageSize);
        Page<KnowledgeBaseListDO> pageResult = knowledgeBaseListMapper.selectPage(page, queryWrapper);
        pageResult.getRecords().forEach(record -> record.setIsFolder(0));
        Page<KnowledgeBaseList> knowledgeBaseListPage = new Page<>();
        BeanUtil.copyProperties(pageResult, knowledgeBaseListPage);
        return knowledgeBaseListPage;
    }

    @Override
    public int updateById(KnowledgeBaseList knowledgeBaseList) {
        User user = UserContext.getUser();
        if (!Objects.isNull(user)) {
            knowledgeBaseList.setModifyBy(UserContext.getUser().getUserName());
            knowledgeBaseList.setGmtModified(new Date());
        }
        return knowledgeBaseListMapper.updateById(BeanUtil.copyProperties(knowledgeBaseList, KnowledgeBaseListDO.class));
    }

    @Override
    public List<KnowledgeBaseList> findFileByKbId(Long kbId) {
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper
                .eq("kb_id", kbId)
                .ne("status", KbFileStatusEnums.DELETE.getValue());
        List<KnowledgeBaseListDO> knowledgeBaseListDOS = knowledgeBaseListMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(knowledgeBaseListDOS) ? null : BeanUtil.copyToList(knowledgeBaseListDOS, KnowledgeBaseList.class);
    }

    @Override
    public List<KnowledgeBaseList> recursiveByFolderId(Long folderId) {
        List<KnowledgeBaseList> knowledgeBaseLists = knowledgeBaseListMapper.recursiveByFolderId(folderId);
        return CollectionUtils.isEmpty(knowledgeBaseLists) ? List.of() : knowledgeBaseLists;
    }

    @Override
    public List<KnowledgeBaseList> findFileByKbId(Long kbId, List<Integer> parseTypes) {
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper
                .eq("kb_id", kbId)
                .ne("status", KbFileStatusEnums.DELETE.getValue())
                .in("parse_type", parseTypes);
        List<KnowledgeBaseListDO> knowledgeBaseListDOS = knowledgeBaseListMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(knowledgeBaseListDOS) ? Lists.newArrayList() : BeanUtil.copyToList(knowledgeBaseListDOS, KnowledgeBaseList.class);
    }

    @Override
    public List<KnowledgeBaseList> findFileByKbId(Long kbId, Integer parseType) {
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper
                .lambda().eq(KnowledgeBaseListDO::getKbId, kbId)
                .ne(KnowledgeBaseListDO::getStatus, KbFileStatusEnums.DELETE.getValue())
                .eq(KnowledgeBaseListDO::getTempStatus, TempStatusEnums.PERSISTENCE.getCode())
                .eq(!Objects.isNull(parseType), KnowledgeBaseListDO::getParseType, parseType);
        List<KnowledgeBaseListDO> knowledgeBaseListDOS = knowledgeBaseListMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(knowledgeBaseListDOS) ? Lists.newArrayList() : BeanUtil.copyToList(knowledgeBaseListDOS, KnowledgeBaseList.class);
    }

    @Override
    public KnowledgeBaseList findFileByKbIdAndFileName(Long kbId, String fileName) {
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper
                .eq("kb_id", kbId)
                .eq("file_name", fileName)
                .ne("status", KbFileStatusEnums.DELETE.getValue())
                .last("limit 1");
        KnowledgeBaseListDO knowledgeBaseListDO = knowledgeBaseListMapper.selectOne(queryWrapper);
        return Objects.isNull(knowledgeBaseListDO) ? null : BeanUtil.copyProperties(knowledgeBaseListDO, KnowledgeBaseList.class);
    }

    @Override
    public Map<Long, KnowledgeBaseFile> findFileInfo(List<Long> kbIds) {
        if (CollectionUtils.isEmpty(kbIds))
            Maps.newHashMap();
        Map<Long, KnowledgeBaseFileDO> fileMap = knowledgeBaseListMapper.selectFiles(kbIds);
        Map<Long, KnowledgeBaseFile> map = new HashMap<>(fileMap.size());
        for (Map.Entry<Long, KnowledgeBaseFileDO> entry : fileMap.entrySet()) {
            map.put(entry.getKey(), BeanUtil.copyProperties(entry.getValue(), KnowledgeBaseFile.class));
        }
        return map;
    }

    @Override
    public KnowledgeBaseList findById(Long id) {
        if (Objects.isNull(id))
            return null;
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.in("id", id)
                .ne("status", KbFileStatusEnums.DELETE.getValue())
                .last("limit 1");
        KnowledgeBaseListDO knowledgeBaseListDO = knowledgeBaseListMapper.selectOne(queryWrapper);
        return Objects.isNull(knowledgeBaseListDO) ? null : BeanUtil.copyProperties(knowledgeBaseListDO, KnowledgeBaseList.class);
    }

    @Override
    public Boolean updateEnable(List<Long> fileIds, Integer enableStatus) {
        if (CollectionUtils.isEmpty(fileIds))
            return false;
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.in("id", fileIds);
        KnowledgeBaseListDO update = new KnowledgeBaseListDO();
        update.setIsEnable(enableStatus);
        update.setModifyBy(UserContext.getUser().getUserName());
        update.setGmtModified(new Date());
        return knowledgeBaseListMapper.update(update, queryWrapper) > 0;
    }

    @Override
    public List<KnowledgeBaseList> findByIds(List<Long> fileIds) {
        if (CollectionUtils.isEmpty(fileIds))
            return Lists.newArrayList();
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.in("id", fileIds)
                .ne("status", KbFileStatusEnums.DELETE.getValue())
                .orderByDesc("gmt_create");
        List<KnowledgeBaseListDO> knowledgeBaseListDOS = knowledgeBaseListMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(knowledgeBaseListDOS) ? Lists.newArrayList() : BeanUtil.copyToList(knowledgeBaseListDOS, KnowledgeBaseList.class);
    }

    @Override
    public KnowledgeBaseList findFileByKbIdAndNameFuzzy(Long kbId, String fileNameFuzzy) {
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper
                .eq("kb_id", kbId)
                .like("file_name", fileNameFuzzy)
                .ne("status", KbFileStatusEnums.DELETE.getValue())
                .last("limit 1");
        KnowledgeBaseListDO knowledgeBaseListDO = knowledgeBaseListMapper.selectOne(queryWrapper);
        return Objects.isNull(knowledgeBaseListDO) ? null : BeanUtil.copyProperties(knowledgeBaseListDO, KnowledgeBaseList.class);
    }

    @Override
    public List<KnowledgeBaseList> findFileByKbIdAndFileStatus(Long kbId, List<Integer> parseStatus, List<Integer> extractStatus) {
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper
                .eq("kb_id", kbId)
                .and(status -> status
                        .in(!CollectionUtils.isEmpty(parseStatus), "status", parseStatus)
                        .or(faq_extract_status -> faq_extract_status.in(!CollectionUtils.isEmpty(extractStatus), "faq_extract_status", extractStatus)));
        List<KnowledgeBaseListDO> knowledgeBaseListDOS = knowledgeBaseListMapper.selectList(queryWrapper);
        return BeanUtil.copyToList(knowledgeBaseListDOS, KnowledgeBaseList.class);
    }

    @Override
    public boolean deleteByIds(List<Long> ids) {
        if (CollectionUtils.isEmpty(ids))
            return false;
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.in("id", ids);
        KnowledgeBaseListDO knowledgeBaseListDO = new KnowledgeBaseListDO();
        knowledgeBaseListDO.setStatus(KbFileStatusEnums.DELETE.getValue());
        return knowledgeBaseListMapper.update(knowledgeBaseListDO, queryWrapper) > 0;
    }

    @Override
    public void updateExtractStatusByFilePaths(List<String> filePaths, Integer extractStatus) {
        if (CollectionUtils.isEmpty(filePaths)) {
            return;
        }
        knowledgeBaseListMapper.updateExtractStatusByFilePaths(filePaths, extractStatus);
    }

    @Override
    public List<KnowledgeBaseList> findFileByKbIdAndType(Long kbId, Integer fileListType) {
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper
                .eq("kb_id", kbId)
                .ne("status", KbFileStatusEnums.DELETE.getValue());

        if (FileListTypeEnums.FILE_LIST.getCode().equals(fileListType) )
            queryWrapper.in("parse_type", Arrays.asList(ParseTypeEnums.FILE_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode()));
        else if (FileListTypeEnums.FAQ_LIST.getCode().equals(fileListType))
            queryWrapper.in("parse_type", Arrays.asList(ParseTypeEnums.FAQ_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode()));
        else if (FileListTypeEnums.GRAPH_LIST.getCode().equals(fileListType))
            queryWrapper.in("parse_type", Arrays.asList(ParseTypeEnums.GRAPH_PARSE.getCode()));
        else if (FileListTypeEnums.DOC_QA.getCode().equals(fileListType)) {
            queryWrapper.in("parse_type", Arrays.asList(ParseTypeEnums.DOC_QA.getCode()));
            queryWrapper.eq("temp_status", TempStatusEnums.PERSISTENCE.getCode());
        }


        List<KnowledgeBaseListDO> knowledgeBaseListDOS = knowledgeBaseListMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(knowledgeBaseListDOS) ? Lists.newArrayList() : BeanUtil.copyToList(knowledgeBaseListDOS, KnowledgeBaseList.class);
    }

    @Override
    public List<KnowledgeBaseList> findFileMaxVersion(Long kbId, Integer fileListType) {
        List<KnowledgeBaseListDO> knowledgeBaseListDOS = knowledgeBaseListMapper.findFileMaxVersion(kbId, fileListType);
        return CollectionUtils.isEmpty(knowledgeBaseListDOS) ? Lists.newArrayList() : BeanUtil.copyToList(knowledgeBaseListDOS, KnowledgeBaseList.class);
    }

    @Override
    public Page<KnowledgeBaseList> parentList(Long kbId, Integer fileListType, String fuzzy, Integer status, Integer faqExtractStatus, Integer showType, List<Long> kbIds, Long pageNo, Long pageSize) {
        Long total = knowledgeBaseListMapper.parentListCount(kbId, fileListType, fuzzy, status, faqExtractStatus, showType, kbIds);
        Long offSet = (pageNo - 1) * pageSize;
        List<KnowledgeBaseListDO> knowledgeBaseListDOS = knowledgeBaseListMapper.parentList(kbId, fileListType, fuzzy, status, faqExtractStatus, showType, kbIds, offSet, pageSize);
        Page<KnowledgeBaseList> knowledgeBaseListPage = new Page<>();
        knowledgeBaseListPage.setTotal(Objects.isNull(total) ? 0 : total);
        knowledgeBaseListPage.setCurrent(pageNo);
        knowledgeBaseListPage.setRecords(BeanUtil.copyToList(knowledgeBaseListDOS, KnowledgeBaseList.class));
        return knowledgeBaseListPage;
    }

    @Override
    public List<KnowledgeBaseList> findByFolderId(Long folderId) {
        if (Objects.isNull(folderId))
            return Lists.newArrayList();
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.in("folder_id", folderId);
        queryWrapper.ne("status", KbFileStatusEnums.DELETE.getValue());
        List<KnowledgeBaseListDO> knowledgeBaseListDOS = knowledgeBaseListMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(knowledgeBaseListDOS) ? Lists.newArrayList() : BeanUtil.copyToList(knowledgeBaseListDOS, KnowledgeBaseList.class);
    }

    @Override
    public Page<KbFileExt> folderList(Long kbId, Integer fileListType, List<Integer> statusList, Integer faqExtractStatus, String fuzzy, Long folderId, Long pageNo, Long pageSize) {
        Map<String, Object> params = Maps.newHashMap();
        buildParams(kbId, fileListType, statusList, faqExtractStatus, fuzzy, folderId, pageNo, pageSize, params);
        Integer count = knowledgeBaseListMapper.folderListCount(params);
        List<KbFileExt> kbFileDOS = knowledgeBaseListMapper.folderList(params);
        Page<KbFileExt> page = new PageDTO<>();
        page.setRecords(kbFileDOS);
        page.setTotal(count);
        page.setCurrent(pageNo);
        page.setSize(pageSize);
        return page;
    }

    @Override
    public Page<KbFileExt> folderAndFileList(FolderAndFilerReq params, Integer pageNo, Integer pageSize) {
        Page<KbFileExt> page = new Page<>(pageNo, pageSize);
        return knowledgeBaseListMapper.folderAndFileList(page, params);
    }

    private void buildParams(Long kbId, Integer fileListType, List<Integer> statusList, Integer faqExtractStatus, String fuzzy, Long folderId, Long pageNo, Long pageSize, Map<String, Object> params) {
        List<Integer> parsetypeList = null;
        if (FileListTypeEnums.FILE_LIST.getCode().equals(fileListType))
            parsetypeList = Arrays.asList(ParseTypeEnums.FILE_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode());
        else if (FileListTypeEnums.FAQ_LIST.getCode().equals(fileListType))
            parsetypeList = Arrays.asList(ParseTypeEnums.FAQ_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode());
        else if (FileListTypeEnums.GRAPH_LIST.getCode().equals(fileListType)) {
            // R14-LIVE-04：图谱解析不新建 parse_type=3 的行，而是在原文件行上置
            // graph_parse_status（见 graphParse 实现）。原实现按 parse_type=3 过滤，
            // 导致解析成功也永远查不到：实测 kb_9 十个文件 graph_parse_status=4，
            // 图谱增强页仍显示"暂无数据"。改为按文档类 parse_type 取全集，
            // 再用 graphParsedOnly 过滤 graph_parse_status。
            parsetypeList = Arrays.asList(ParseTypeEnums.FILE_PARSE.getCode(),
                    ParseTypeEnums.FAQ_FILE_PARSE.getCode());
            params.put("graphParsedOnly", Boolean.TRUE);
        }
        else if (FileListTypeEnums.DOC_QA.getCode().equals(fileListType))
            parsetypeList = Collections.singletonList(ParseTypeEnums.DOC_QA.getCode());

        Long offset = (pageNo - 1) * pageSize;

        params.put("kbId", kbId);
        params.put("parsetypeList", parsetypeList);
        params.put("statusList", statusList);
        params.put("faqExtractStatus", faqExtractStatus);
        params.put("fuzzy", fuzzy);
        params.put("folderId", folderId);
        params.put("userId", UserContext.getUser().getUserId());
        params.put("offset", offset);
        params.put("pageSize", pageSize);
    }

    @Override
    public LinkedHashSet<KbFileExt> fileList(Set<Long> kbIds, Integer status, String kbName, Set<Long> folderIds, String userName, boolean withFolder) {
//        if (!CollectionUtils.isEmpty(kbIds)) {
        // 并发时，线程间使用相同表存在问题，取消手动维护临时表方式，改用sql创建临时表。
//            knowledgeBaseListMapper.dropTmpIdsTable();
//            knowledgeBaseListMapper.createTmpIdsTable();
//            knowledgeBaseListMapper.insertTmpIds(kbIds);
//        }
        return knowledgeBaseListMapper.fileList(new ArrayList<>(kbIds), status, kbName, folderIds, userName, withFolder);
    }

    @Override
    public Page<KbFileExt> onlyFileList(Page<KbFileExt> page, Set<Long> kbIds, Integer status, String kbName, Set<Long> folderIds, String userName) {
//        if (!CollectionUtils.isEmpty(kbIds)) {
        // 并发时，线程间使用相同表存在问题，取消手动维护临时表方式，改用sql创建临时表。
//            knowledgeBaseListMapper.dropTmpIdsTable();
//            knowledgeBaseListMapper.createTmpIdsTable();
//            knowledgeBaseListMapper.insertTmpIds(kbIds);
//        }
        return knowledgeBaseListMapper.onlyFileList(page, new ArrayList<>(kbIds), new int[]{KbFileStatusEnums.PARSE_SUCCESS.getValue()}, kbName, folderIds, userName);
    }

    @Override
    public List<KbFileExt> onlyFileListByTime(Set<Long> kbIds, String kbName, Set<Long> folderIds, String userName, LocalDateTime startTime, LocalDateTime endTime, int[] statusArray) {
        List<KbFileExt> kbFileExts = knowledgeBaseListMapper.onlyFileListByTime(new ArrayList<>(kbIds), statusArray, kbName, folderIds, userName, startTime, endTime);
        return CollectionUtils.isEmpty(kbFileExts) ? Collections.emptyList() : kbFileExts;
    }

    @Override
    public List<KnowledgeBaseList> findByFolderIds(List<Long> folderIds, List<Integer> status) {
        if (CollectionUtils.isEmpty(folderIds))
            return Lists.newArrayList();
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.lambda().in(KnowledgeBaseListDO::getFolderId, folderIds);
        queryWrapper.lambda().in(!CollectionUtils.isEmpty(status), KnowledgeBaseListDO::getStatus, status);
        List<KnowledgeBaseListDO> knowledgeBaseListDOS = knowledgeBaseListMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(knowledgeBaseListDOS) ? Lists.newArrayList() : BeanUtil.copyToList(knowledgeBaseListDOS, KnowledgeBaseList.class);
    }

    @Override
    public List<KnowledgeBaseList> findByFolderIds(List<Long> folderIds, List<Integer> parseStatus, List<Integer> faqExtractStatus, List<Integer> graphParseStatus) {
        if (CollectionUtils.isEmpty(folderIds))
            return Lists.newArrayList();
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.lambda().in(KnowledgeBaseListDO::getFolderId, folderIds);
        queryWrapper.lambda().in(!CollectionUtils.isEmpty(parseStatus), KnowledgeBaseListDO::getStatus, parseStatus);
        queryWrapper.lambda().in(!CollectionUtils.isEmpty(faqExtractStatus), KnowledgeBaseListDO::getFaqExtractStatus, faqExtractStatus);
        queryWrapper.lambda().in(!CollectionUtils.isEmpty(graphParseStatus), KnowledgeBaseListDO::getGraphParseStatus, graphParseStatus);
        List<KnowledgeBaseListDO> knowledgeBaseListDOS = knowledgeBaseListMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(knowledgeBaseListDOS) ? Lists.newArrayList() : BeanUtil.copyToList(knowledgeBaseListDOS, KnowledgeBaseList.class);
    }

    @Override
    public void updateExtractStatusByIds(List<Long> ids, Integer extractStatus) {
        if (CollectionUtils.isEmpty(ids)) {
            return;
        }
        knowledgeBaseListMapper.updateExtractStatusByIds(ids, extractStatus);
    }

    @Override
    public List<KnowledgeBaseList> findNoParseFiles(Long kbId, List<Integer> parseTypes) {
        if (Objects.isNull(kbId) || CollectionUtils.isEmpty(parseTypes))
            return Lists.newArrayList();
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("kb_id", kbId)
                .in("parse_type", parseTypes)
                .in("status", Arrays.asList(KbFileStatusEnums.NORMAL.getValue(), KbFileStatusEnums.PARSE_SUCCESS.getValue(), KbFileStatusEnums.PARSE_FAIL.getValue()));
        List<KnowledgeBaseListDO> knowledgeBaseListDOS = knowledgeBaseListMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(knowledgeBaseListDOS) ? Lists.newArrayList() : BeanUtil.copyToList(knowledgeBaseListDOS, KnowledgeBaseList.class);
    }

    @Override
    public List<KnowledgeBaseList> findNoExtractFiles(Long kbId, List<Integer> parseTypes) {
        if (Objects.isNull(kbId) || CollectionUtils.isEmpty(parseTypes))
            return Lists.newArrayList();
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("kb_id", kbId)
                .in("parse_type", parseTypes)
                .in("faq_extract_status", Arrays.asList(FaqExtractStatusEnums.NO_EXTRACT.getValue(), FaqExtractStatusEnums.EXTRACT_FAIL.getValue()))
                .ne("status", KbFileStatusEnums.DELETE.getValue());
        List<KnowledgeBaseListDO> knowledgeBaseListDOS = knowledgeBaseListMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(knowledgeBaseListDOS) ? Lists.newArrayList() : BeanUtil.copyToList(knowledgeBaseListDOS, KnowledgeBaseList.class);
    }

    @Override
    public KnowledgeBaseList findByParentFileName(Long kbId, String parentFileName) {
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("kb_id", kbId)
                .eq("parent_file_name", parentFileName)
                .ne("status", KbFileStatusEnums.DELETE.getValue());
        List<KnowledgeBaseListDO> knowledgeBaseListDOS = knowledgeBaseListMapper.selectList(queryWrapper);
        if (!CollectionUtils.isEmpty(knowledgeBaseListDOS)) {
            return BeanUtil.copyProperties(knowledgeBaseListDOS.get(0), KnowledgeBaseList.class);
        }
        return null;
    }

    @Override
    public List<KnowledgeBaseList> queryList(Long kbId, List<Integer> types) {
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("kb_id", kbId)
                .in(!CollectionUtils.isEmpty(types), "parse_type", types)
                .ne("status", KbFileStatusEnums.DELETE.getValue());
        List<KnowledgeBaseListDO> knowledgeBaseListDOS = knowledgeBaseListMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(knowledgeBaseListDOS) ? List.of() : BeanUtil.copyToList(knowledgeBaseListDOS, KnowledgeBaseList.class);
    }

    @Override
    public List<KnowledgeBaseList> queryListWithPermission(Long kbId, Long deptId, Long userId) {
        List<KnowledgeBaseListDO> knowledgeBaseListDOS = knowledgeBaseListMapper.queryListWithPermission(kbId, deptId, userId, 1, 1, null);
        return CollectionUtils.isEmpty(knowledgeBaseListDOS) ? Lists.newArrayList() : BeanUtil.copyToList(knowledgeBaseListDOS, KnowledgeBaseList.class);
    }

    @Override
    public List<KnowledgeBaseList> queryListWithPermission(Long kbId, Long deptId, Long userId, Integer folderType, Integer parseType, List<Integer> bizTypes) {
        List<KnowledgeBaseListDO> knowledgeBaseListDOS = knowledgeBaseListMapper.queryListWithPermission(kbId, deptId, userId, folderType, parseType, bizTypes);
        return CollectionUtils.isEmpty(knowledgeBaseListDOS) ? Lists.newArrayList() : BeanUtil.copyToList(knowledgeBaseListDOS, KnowledgeBaseList.class);
    }

    @Override
    public List<KnowledgeBaseList> queryNoPermissionFiles(Long kbId, Long deptId, Long userId) {
        List<KnowledgeBaseListDO> knowledgeBaseListDOS = knowledgeBaseListMapper.queryNoPermissionFiles(kbId, deptId, userId);
        return CollectionUtils.isEmpty(knowledgeBaseListDOS) ? Lists.newArrayList() : BeanUtil.copyToList(knowledgeBaseListDOS, KnowledgeBaseList.class);
    }

    @Override
    public List<KnowledgeBaseList> getByKbIdAndUid(Long kbId, List<String> fileUids, Integer tempStatus) {
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("kb_id", kbId)
                .eq(!Objects.isNull(tempStatus), "temp_status", tempStatus)
                .in(!CollectionUtils.isEmpty(fileUids), "uid", fileUids)
                .ne("status", KbFileStatusEnums.DELETE.getValue());
        List<KnowledgeBaseListDO> knowledgeBaseListDOS = knowledgeBaseListMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(knowledgeBaseListDOS) ? null : BeanUtil.copyToList(knowledgeBaseListDOS, KnowledgeBaseList.class);
    }

    @Override
    public List<KnowledgeBaseList> findByUids(List<String> uids) {
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.in("uid", uids)
                .ne("status", KbFileStatusEnums.DELETE.getValue());
        List<KnowledgeBaseListDO> knowledgeBaseListDOS = knowledgeBaseListMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(knowledgeBaseListDOS) ? null : BeanUtil.copyToList(knowledgeBaseListDOS, KnowledgeBaseList.class);
    }

    @Override
    public Boolean updateTempStatusByUid(List<String> fileUids, Integer temStatus) {
        if (CollectionUtils.isEmpty(fileUids))
            return false;
        knowledgeBaseListMapper.updateTempStatusByUid(fileUids, temStatus);
        return true;
    }

    @Override
    public KnowledgeBaseFileDTO findFile(Long kbId, String fileName, Integer type) {
        List<Integer> parsetypeList = null;
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        if (FileListTypeEnums.FILE_LIST.getCode().equals(type))
            parsetypeList = Arrays.asList(ParseTypeEnums.FILE_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode());
        else if (FileListTypeEnums.FAQ_LIST.getCode().equals(type))
            parsetypeList = Arrays.asList(ParseTypeEnums.FAQ_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode());
        else if (FileListTypeEnums.GRAPH_LIST.getCode().equals(type))
            parsetypeList = Arrays.asList(ParseTypeEnums.GRAPH_PARSE.getCode());
        else if (FileListTypeEnums.DOC_QA.getCode().equals(type)) {
            parsetypeList = Arrays.asList(ParseTypeEnums.DOC_QA.getCode());
            queryWrapper.eq("temp_status", TempStatusEnums.PERSISTENCE.getCode());
        }

        queryWrapper.eq("kb_id", kbId)
                .eq("file_name", fileName)
                .ne("status", KbFileStatusEnums.DELETE.getValue())
                .in("parse_type", parsetypeList)
                .last("limit 1");
        KnowledgeBaseListDO knowledgeBaseListDO = knowledgeBaseListMapper.selectOne(queryWrapper);
        return Objects.isNull(knowledgeBaseListDO) ? null : BeanUtil.copyProperties(knowledgeBaseListDO, KnowledgeBaseFileDTO.class);
    }

    @Override
    public List<KnowledgeBaseList> findByKbIdAndGroupIds(Long kbId, List<String> groupIds) {
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("kb_id", kbId)
                .in("group_id", groupIds)
                .ne("status", KbFileStatusEnums.DELETE.getValue())
                .in("parse_type", Arrays.asList(ParseTypeEnums.FILE_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode()));
        List<KnowledgeBaseListDO> kbFiles = knowledgeBaseListMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(kbFiles) ? null : BeanUtil.copyToList(kbFiles, KnowledgeBaseList.class);
    }

    @Override
    public List<KnowledgeBaseList> findByKbId(Long kbId, List<Integer> parseTypes, List<Long> excludeFolderIds, List<Long> excludeFileIds, List<Integer> parseStatus, List<Integer> faqExtractStatus) {
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("kb_id", kbId)
                .ne("status", KbFileStatusEnums.DELETE.getValue())
                .notIn(!CollectionUtils.isEmpty(excludeFolderIds), "folder_id", excludeFolderIds)
                .notIn(!CollectionUtils.isEmpty(excludeFileIds), "id", excludeFileIds)
                .in(!CollectionUtils.isEmpty(parseStatus), "status", parseStatus)
                .in(!CollectionUtils.isEmpty(faqExtractStatus), "faq_extract_status", faqExtractStatus)
                .in("parse_type", parseTypes);
        List<KnowledgeBaseListDO> kbFiles = knowledgeBaseListMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(kbFiles) ? null : BeanUtil.copyToList(kbFiles, KnowledgeBaseList.class);
    }

    @Override
    public Boolean updateMultiversion(List<Long> fileIds, String parentFileName, String groupId, String versionDate) {
        LambdaUpdateWrapper<KnowledgeBaseListDO> update = new LambdaUpdateWrapper<>();
        update.in(KnowledgeBaseListDO::getId, fileIds)
                .ne(KnowledgeBaseListDO::getStatus, KbFileStatusEnums.DELETE.getValue())
                .set(KnowledgeBaseListDO::getParentFileName, parentFileName)
                .set(KnowledgeBaseListDO::getGroupId, groupId)
                .set(KnowledgeBaseListDO::getReviseDate, versionDate);
        return knowledgeBaseListMapper.update(null, update) > 0;
    }

    @Override
    public List<KnowledgeBaseList> collectList(Long kbId, Integer fileListType) {
        List<KnowledgeBaseListDO> knowledgeBaseListDOS = knowledgeBaseListMapper.parentList(kbId, fileListType, null, null, null, 2, null, 0L, 1000L);
        return CollectionUtils.isEmpty(knowledgeBaseListDOS) ? null : BeanUtil.copyToList(knowledgeBaseListDOS, KnowledgeBaseList.class);
    }

    @Override
    public KnowledgeBaseList findByKbIdAndGroupId(Long kbId, String groupId) {
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("kb_id", kbId)
                .eq(StringUtils.isNotBlank(groupId), "group_id", groupId)
                .ne("status", KbFileStatusEnums.DELETE.getValue())
                .in("parse_type", Arrays.asList(ParseTypeEnums.FILE_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode()))
                .last("limit 1");
        KnowledgeBaseListDO knowledgeBaseListDO = knowledgeBaseListMapper.selectOne(queryWrapper);
        return Objects.isNull(knowledgeBaseListDO) ? null : BeanUtil.copyProperties(knowledgeBaseListDO, KnowledgeBaseList.class);
    }

    @Override
    public List<KnowledgeBaseList> findByKbIdAndGroupIds(Long kbId, List<String> groupIds, List<Integer> parseTypes) {
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("kb_id", kbId)
                .in("group_id", groupIds)
                .ne("status", KbFileStatusEnums.DELETE.getValue())
                .in("parse_type", parseTypes);
        List<KnowledgeBaseListDO> kbFiles = knowledgeBaseListMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(kbFiles) ? null : BeanUtil.copyToList(kbFiles, KnowledgeBaseList.class);
    }

    @Override
    public List<KnowledgeBaseList> scatterList(Long kbId, Integer fileListType) {
        List<KnowledgeBaseListDO> knowledgeBaseListDOS = knowledgeBaseListMapper.parentList(kbId, fileListType,
                null, null, null, 3, null, 0L, 1000L);
        return CollectionUtils.isEmpty(knowledgeBaseListDOS) ? null : BeanUtil.copyToList(knowledgeBaseListDOS, KnowledgeBaseList.class);
    }

    @Override
    public KnowledgeBaseList findFileGroup(Long kbId, String groupId, List<Integer> parseTypes) {
        KnowledgeBaseListDO knowledgeBaseListDO = knowledgeBaseListMapper.findFileGroup(kbId, groupId, parseTypes);
        return Objects.isNull(knowledgeBaseListDO) ? null : BeanUtil.copyProperties(knowledgeBaseListDO, KnowledgeBaseList.class);
    }

    @Override
    public void transferFile(Long id, Long folderId) {
        knowledgeBaseListMapper.transferFile(id, folderId);
    }

    @Override
    public void transferFileBatch(List<Long> ids, Long folderId) {
        if (!CollectionUtils.isEmpty(ids))
            knowledgeBaseListMapper.transferFileBatch(ids, folderId);
    }

    @Override
    public List<KnowledgeBaseList> findByFolderId(Long kbId, Integer type, Long folerId) {
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.lambda().eq(KnowledgeBaseListDO::getKbId, kbId)
                .eq(!Objects.isNull(type), KnowledgeBaseListDO::getParseType, type)
                .ne(KnowledgeBaseListDO::getStatus, KbFileStatusEnums.DELETE.getValue());
        if (Objects.isNull(folerId))
            queryWrapper.lambda().isNull(KnowledgeBaseListDO::getFolderId);
        else
            queryWrapper.lambda().eq(KnowledgeBaseListDO::getFolderId, folerId);
        List<KnowledgeBaseListDO> knowledgeBaseListDOs = knowledgeBaseListMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(knowledgeBaseListDOs) ? Lists.newArrayList() : BeanUtil.copyToList(knowledgeBaseListDOs, KnowledgeBaseList.class);

    }

    @Override
    public List<KnowledgeBaseList> findFileByFolder(List<Long> folderIds) {
        if (CollectionUtils.isEmpty(folderIds))
            return Lists.newArrayList();
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.in("folder_id", folderIds);
        queryWrapper.ne("status", KbFileStatusEnums.DELETE.getValue());
        List<KnowledgeBaseListDO> knowledgeBaseListDOS = knowledgeBaseListMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(knowledgeBaseListDOS) ? Lists.newArrayList() : BeanUtil.copyToList(knowledgeBaseListDOS, KnowledgeBaseList.class);
    }

    @Override
    public List<KnowledgeBaseList> findFileByFilePaths(Long kbId, List<String> filePaths, Integer type) {
        if (Objects.isNull(kbId) || CollectionUtils.isEmpty(filePaths) || Objects.isNull(type))
            return null;
        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.lambda()
                .eq(KnowledgeBaseListDO::getKbId, kbId)
                .in(KnowledgeBaseListDO::getFilePath, filePaths)
                .eq(KnowledgeBaseListDO::getParseType, type)
                .ne(KnowledgeBaseListDO::getStatus, KbFileStatusEnums.DELETE.getValue());
        List<KnowledgeBaseListDO> knowledgeBaseListDOS = knowledgeBaseListMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(knowledgeBaseListDOS) ? Lists.newArrayList() : BeanUtil.copyToList(knowledgeBaseListDOS, KnowledgeBaseList.class);
    }

    @Override
    public Long getSequenceCodeByFileId(Long fileId) {
//        QueryWrapper<KnowledgeBaseListDO> queryWrapper = new QueryWrapper<>();
//        queryWrapper.lambda()
//                .lt(KnowledgeBaseListDO::getId, fileId)
//                .in(KnowledgeBaseListDO::getStatus, Arrays.asList(KbFileStatusEnums.PARSE_WAIT.getValue(),KbFileStatusEnums.PARSE_ING.getValue()))
//                .in(KnowledgeBaseListDO::getParseType,Arrays.asList(ParseTypeEnums.FILE_PARSE.getCode(),ParseTypeEnums.FAQ_PARSE.getCode(),ParseTypeEnums.FAQ_FILE_PARSE.getCode()));
//        return knowledgeBaseListMapper.selectCount(queryWrapper);

        return knowledgeBaseListMapper.getSequenceCodeByFileId(fileId);
    }
}
