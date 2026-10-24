package com.gientech.tools.database.domain.service;

import com.gientech.tools.database.domain.entity.TLTableFile;

import java.util.List;

public interface TLTableFileDomainService {
    Boolean save(TLTableFile tlTableFile);
    List<TLTableFile> listByTableId(Long tableId);
    List<TLTableFile> listUploadedByTableId(Long tableId);
    TLTableFile findById(Long fileId);
    TLTableFile findByTableIdAndDatabaseId(Long tableId, Long databaseId);
    List<TLTableFile> findByDatabaseId(Long databaseId);
    List<TLTableFile> findImportedByDatabaseId(Long databaseId);
    Boolean updateById(TLTableFile tlTableFile);
    Integer deleteById(Long fileId);
    Integer deleteByIdAndStatus(Long fileId, String status);
    Integer deleteByTableId(Long tableId);
    Integer deleteByTableId(Long tableId, String status);
    Integer deleteNotImportFileByName(Long fileId, String originalFileName);
}
