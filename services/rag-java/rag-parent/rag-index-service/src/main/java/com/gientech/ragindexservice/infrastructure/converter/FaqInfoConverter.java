package com.gientech.ragindexservice.infrastructure.converter;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.dto.FaqDTO;
import com.gientech.ragindexservice.domain.entity.FaqEsInfo;
import com.gientech.ragindexservice.domain.entity.FaqInfo;
import com.gientech.ragindexservice.domain.model.FaqInfoExt;
import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;

import java.util.List;
import java.util.Objects;

@Mapper
public interface FaqInfoConverter {
    FaqInfoConverter INSTANCE = Mappers.getMapper(FaqInfoConverter.class);

    default FaqInfo resultData2FaqInfo(FaqEsInfo.FaqEsInfoResultData resultData) {
        FaqInfo faqInfo = new FaqInfo();
        FaqEsInfo.FaqEsInfoSource source = resultData.getSource();
        FaqEsInfo.FaqEsMetadata metadata = source.getMetadata();
        faqInfo.setFaqType(metadata.getFaqType());
        faqInfo.setPk(Long.valueOf(metadata.getPk()));
        faqInfo.setRelatedPk(Long.valueOf(metadata.getRelatedPk()));
        faqInfo.setPageContent(source.getPageContent());
        faqInfo.setAnswer(metadata.getAnswer());
        faqInfo.setQuestion(metadata.getQuestion());
        faqInfo.setDocumentId(Objects.isNull(metadata.getDocumentId()) ? null : Long.valueOf(metadata.getDocumentId()));
        faqInfo.setFolderId(Objects.isNull(metadata.getFolderId()) ? null : Long.valueOf(metadata.getFolderId()));
        faqInfo.setSourceFile(metadata.getSource());
        faqInfo.setStatus(metadata.getStatus());
        faqInfo.setGmtCreate(metadata.getCreateTime());
        faqInfo.setGmtModified(metadata.getUpdateTime());
        return faqInfo;
    }

    List<FaqInfo> resultDataList2FaqInfoList(List<FaqEsInfo.FaqEsInfoResultData> resultData);

    default Page<FaqDTO> faqInfoPage2FaqDTOPage(Page<FaqInfo> faqInfoPage) {
        Page<FaqDTO> faqDTOPage = new Page<>(faqInfoPage.getCurrent(), faqInfoPage.getSize());
        faqDTOPage.setRecords(BeanUtil.copyToList(faqInfoPage.getRecords(), FaqDTO.class));
        faqDTOPage.setTotal(faqInfoPage.getTotal());
        faqDTOPage.setPages(faqInfoPage.getPages());
        return faqDTOPage;
    }

    default Page<FaqDTO> faqInfoExtPage2FaqDTOPage(Page<FaqInfoExt> faqInfoExtPage) {
        Page<FaqDTO> faqDTOPage = new Page<>(faqInfoExtPage.getCurrent(), faqInfoExtPage.getSize());
        faqDTOPage.setRecords(BeanUtil.copyToList(faqInfoExtPage.getRecords(), FaqDTO.class));
        faqDTOPage.setTotal(faqInfoExtPage.getTotal());
        faqDTOPage.setPages(faqInfoExtPage.getPages());
        return faqDTOPage;
    }

}
