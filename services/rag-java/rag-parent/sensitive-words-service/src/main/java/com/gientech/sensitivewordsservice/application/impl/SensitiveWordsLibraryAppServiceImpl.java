package com.gientech.sensitivewordsservice.application.impl;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragcommon.sensitive.dto.SensitiveWordsDTO;
import com.gientech.sensitivewordsservice.application.SensitiveWordsLibraryAppService;
import com.gientech.sensitivewordsservice.application.remote.SearchConfigClient;
import com.gientech.sensitivewordsservice.domain.convertor.SensitiveWordsConvertor;
import com.gientech.sensitivewordsservice.domain.entity.SensitiveWords;
import com.gientech.sensitivewordsservice.domain.service.SensitiveWordsLibraryDomainService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.util.Arrays;
import java.util.LinkedHashSet;
import java.util.List;

@Slf4j
@Service
public class SensitiveWordsLibraryAppServiceImpl implements SensitiveWordsLibraryAppService {

    @Autowired
    private SensitiveWordsLibraryDomainService sensitiveWordsLibraryDomainService;

    @Autowired
    private SearchConfigClient searchConfigClient;

    /**
     * 创建敏感词库
     *
     * @param sensitiveWords 敏感词库
     * @return id
     */
    @Override
    public Long createWordsLibrary(SensitiveWords sensitiveWords) {
        return sensitiveWordsLibraryDomainService.createWordsLibrary(sensitiveWords);
    }

    /**
     * 删除敏感词库
     *
     * @param id id
     * @return 成功/失败
     */
    @Override
    public Boolean deleteWordsLibrary(Long id) {
        //删除敏感词库
        sensitiveWordsLibraryDomainService.deleteWordsLibrary(id);
        //更新助手配置
        searchConfigClient.updateSensitiveWord(id);
        return Boolean.TRUE;
    }

    /**
     * 根据id修改敏感词库
     *
     * @param sensitiveWords 敏感词库
     * @return 新的敏感词库信息
     */
    @Override
    public SensitiveWords updateWordsLibraryById(SensitiveWords sensitiveWords) {
        return sensitiveWordsLibraryDomainService.updateWordsLibraryById(sensitiveWords);
    }

    /**
     * 根据id查询敏感词库详细信息
     *
     * @param id id
     * @return 敏感词库信息，包含敏感词列表
     */
    @Override
    public SensitiveWords queryWordsLibraryById(Long id,Integer start,Integer end) {
        SensitiveWords sensitiveWords = sensitiveWordsLibraryDomainService.queryWordsLibraryById(id);
        return sensitiveWords;
    }

    /**
     * 分页查询敏感词库，筛选条件有name
     *
     * @param
     * @return 分页结构数据
     */
    @Override
    public Page<SensitiveWords> pageQuery(String name, List<Long> ids, Integer pageNo, Integer pageSize) {
        try {
            return sensitiveWordsLibraryDomainService.pageQuery( name, ids,pageNo, pageSize);
        } catch (Exception e) {
            log.error("pageQueryWordsLibrary error:", e);
            throw new ApplicationException("分页查询敏感词库失败");
        }
    }

    @Override
    public List<SensitiveWordsDTO> getListByIds(Long[] ids) {
        return SensitiveWordsConvertor.INSTANCE.wordsList2WordsDTOList(sensitiveWordsLibraryDomainService.getListByIds(Arrays.asList(ids)));
    }
}
