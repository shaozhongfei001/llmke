package com.gientech.sensitivewordsservice.application;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.sensitive.dto.SensitiveWordsDTO;
import com.gientech.sensitivewordsservice.domain.entity.SensitiveWords;

import java.util.List;

public interface SensitiveWordsLibraryAppService {

    /**
     * 创建敏感词库
     * @param sensitiveWords 敏感词库
     * @return id
     */
    Long createWordsLibrary(SensitiveWords sensitiveWords);

    /**
     * 删除敏感词库
     * @param id id
     * @return 成功/失败
     */
    Boolean deleteWordsLibrary(Long id);

    /**
     * 根据id修改敏感词库
     * @param sensitiveWords 敏感词库
     * @return 新的敏感词库信息
     */
    SensitiveWords updateWordsLibraryById(SensitiveWords sensitiveWords);


    /**
     * 根据id查询敏感词库详细信息
     * @param id id
     * @return 敏感词库信息，包含敏感词列表
     */
    SensitiveWords queryWordsLibraryById(Long id,Integer start,Integer end);

    /**
     * 分页查询敏感词库，筛选条件有name
     * @param
     * @return
     */
    Page<SensitiveWords> pageQuery(String name, List<Long> ids, Integer pageNo, Integer pageSize);


    List<SensitiveWordsDTO> getListByIds(Long[] ids);
}
