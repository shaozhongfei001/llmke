package com.gientech.ragindexservice.application.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.dto.FolderDTO;
import com.gientech.ragcommon.index.dto.FolderInfoDTO;
import com.gientech.ragcommon.index.dto.SaveFolderInfoReq;
import com.gientech.ragcommon.index.request.*;

import java.util.List;

public interface FolderInfoAppService {

    FolderInfoDTO findById(Long id);

    Boolean save(SaveFolderInfoReq folderInfoReq);

    Boolean rename(UpdateFolderInfoReq folderInfoReq);

    Page<FolderInfoDTO> list(Long pageNo, Long pageSize);

    Boolean deleteById(Long id);

    Boolean fileTransfer(FileTransferReq fileTransferReq);

    Boolean transfer(TransferReq transferReq);

    Boolean transferBatch(TransferBatchReq transferBatchReq);

    List<FolderInfoDTO> leveList(List<Long> kbIds);

    Boolean addLabel(Long folderId, String label);

    /**
     * 查询文档创建者
     * @param id
     * @return
     */
    String queryCreator(Long id);

    List<FolderInfoDTO> recursiveFolderByKb(QueryFolderReq queryFolderReq);

    List<FolderDTO> folderFileList(QueryFolderReq queryFolderReq);
}
