package com.gientech.ragindexservice.infrastructure;

import com.gientech.ragcommon.index.dto.FolderInfoDTO;
import com.gientech.ragcommon.infrastructure.template.TreeBuilder;

import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * @author chenjuan
 * @date 2025/5/19 17:50
 */
public class FolderTreeBuilder extends TreeBuilder<FolderInfoDTO> {
    @Override
    protected Long getId(FolderInfoDTO element) {
        return element.getId();
    }

    @Override
    protected boolean isRoot(FolderInfoDTO element) {
        return Objects.isNull(element.getParentId());
    }

    @Override
    protected List<FolderInfoDTO> createRelations(List<FolderInfoDTO> elements, Map<Long, FolderInfoDTO> elementMap, List<FolderInfoDTO> rootElements) {
        elements.forEach(element -> {
            FolderInfoDTO folderInfoDTO = elementMap.get(element.getParentId());
            if (!Objects.isNull(folderInfoDTO)) {
                folderInfoDTO.getSubFolders().add(element);
            }
        });
        return rootElements;
    }
}



