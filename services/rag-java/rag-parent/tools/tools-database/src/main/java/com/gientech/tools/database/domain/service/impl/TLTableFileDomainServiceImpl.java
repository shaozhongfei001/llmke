package com.gientech.tools.database.domain.service.impl;

import com.gientech.tools.database.domain.entity.TLTableFile;
import com.gientech.tools.database.domain.repository.TLTableFileRepository;
import com.gientech.tools.database.domain.service.TLTableFileDomainService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class TLTableFileDomainServiceImpl implements TLTableFileDomainService {
    private static final Logger log = LoggerFactory.getLogger(TLTableDomainServiceImpl.class);

    @Autowired
    private TLTableFileRepository tlTableFileRepository;

    @Override
    public Boolean save(TLTableFile tlTableFile) {
        return tlTableFileRepository.save(tlTableFile);
    }

    @Override
    public List<TLTableFile> listByTableId(Long tableId) {
        return tlTableFileRepository.listByTableId(tableId);
    }

    @Override
    public List<TLTableFile> listUploadedByTableId(Long tableId) {
        return tlTableFileRepository.listByTableId(tableId);
    }

    @Override
    public TLTableFile findById(Long fileId) {
        return tlTableFileRepository.findById(fileId);
    }

    @Override
    public List<TLTableFile> findByDatabaseId(Long databaseId) {
        return tlTableFileRepository.findByDatabaseId(databaseId);
    }

    @Override
    public TLTableFile findByTableIdAndDatabaseId(Long tableId, Long databaseId) {
        return tlTableFileRepository.findByTableIdAndDatabaseId(tableId, databaseId);
    }

    @Override
    public List<TLTableFile> findImportedByDatabaseId(Long databaseId) {
        return tlTableFileRepository.findImportedByDatabaseId(databaseId);
    }

    @Override
    public Boolean updateById(TLTableFile tlTableFile) {
        return tlTableFileRepository.updateById(tlTableFile);
    }

    @Override
    public Integer deleteById(Long fileId) {
        return tlTableFileRepository.deleteById(fileId);
    }

    @Override
    public Integer deleteByIdAndStatus(Long fileId, String status) {
        return tlTableFileRepository.deleteByIdAndStatus(fileId, status);
    }

    @Override
    public Integer deleteByTableId(Long tableId) {
        return tlTableFileRepository.deleteByTableId(tableId);
    }

    @Override
    public Integer deleteByTableId(Long tableId, String status) {
        return tlTableFileRepository.deleteByTableId(tableId, status);
    }

    @Override
    public Integer deleteNotImportFileByName(Long fileId, String originalFileName) {
        return tlTableFileRepository.deleteNotImportFileByName(fileId, originalFileName);
    }
}
