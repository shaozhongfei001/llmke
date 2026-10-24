package com.gientech.ragindexservice.infrastructure.converter;

import cn.hutool.core.bean.BeanUtil;
import com.alibaba.excel.util.StringUtils;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.gientech.ragcommon.index.dto.KnowledgeBaseFileDTO;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragindexservice.domain.entity.KbFileExt;
import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;
import org.springframework.context.annotation.Bean;

import java.util.Collection;
import java.util.List;

@Mapper
public interface KbFileExtConverter {
    KbFileExtConverter INSTANCE = Mappers.getMapper(KbFileExtConverter.class);

    default KnowledgeBaseFileDTO kbFileExt2KnowledgeBaseFileDTO(KbFileExt kbFileExt) {
        if (kbFileExt == null) {
            return null;
        }

//        KnowledgeBaseFileDTO knowledgeBaseFileDTO = new KnowledgeBaseFileDTO();
//        knowledgeBaseFileDTO.setId(kbFileExt.getId());
//        knowledgeBaseFileDTO.setConvertedFilePath(kbFileExt.getConvertedFilePath());
//        knowledgeBaseFileDTO.setPermission(kbFileExt.getPermission());
//        knowledgeBaseFileDTO.setStatus(kbFileExt.getStatus());
//        knowledgeBaseFileDTO.setChunking(kbFileExt.isChunking());
//        knowledgeBaseFileDTO.setFilePath(kbFileExt.getFilePath());
//        knowledgeBaseFileDTO.setFolderId(kbFileExt.getFolderId());
//        knowledgeBaseFileDTO.setFileName(kbFileExt.getFileName());
//        knowledgeBaseFileDTO.setElementType(kbFileExt.getElementType());
//        knowledgeBaseFileDTO.setParentId(kbFileExt.getParentId());
//        knowledgeBaseFileDTO.setLabel(kbFileExt.getLabel());
//        knowledgeBaseFileDTO.setIsFolder(kbFileExt.getIsFolder());
//        knowledgeBaseFileDTO.setSourceUrl(kbFileExt.getSourceUrl());
//        knowledgeBaseFileDTO.setFolderName(kbFileExt.getFolderName());
//        knowledgeBaseFileDTO.setKbName(kbFileExt.getKbName());
//        knowledgeBaseFileDTO.setKbId(kbFileExt.getKbId());
//        knowledgeBaseFileDTO.setReviseDate(kbFileExt.getReviseDate());
//        knowledgeBaseFileDTO.setFullTextPath(kbFileExt.getFullTextPath());
//        knowledgeBaseFileDTO.setParsedFilePath(kbFileExt.getParsedFilePath());
//        knowledgeBaseFileDTO.setParentFileName(kbFileExt.getParentFileName());
//        knowledgeBaseFileDTO.setParseType(kbFileExt.getParseType());
//        knowledgeBaseFileDTO.setSize(kbFileExt.getFileSize());

        KnowledgeBaseFileDTO knowledgeBaseFileDTO = BeanUtil.copyProperties(kbFileExt,KnowledgeBaseFileDTO.class);
        if (StringUtils.isNotBlank(kbFileExt.getImagePaths())) {
            try {
                ObjectMapper objectMapper = new ObjectMapper();
                List<String> strings = objectMapper.readValue(kbFileExt.getImagePaths(), new TypeReference<List<String>>() {
                });
                knowledgeBaseFileDTO.setImagePaths(strings);
            } catch (JsonProcessingException e) {
                throw new ApplicationException("Failed to deserialize JSON to list");
            }
        }


        return knowledgeBaseFileDTO;
    }

    List<KnowledgeBaseFileDTO> kbFileExts2KnowledgeBaseFileDTOS(Collection<KbFileExt> kbFileExts);
}
