package com.gientech.ragcommon.graph.convertor;


import com.gientech.ragcommon.graph.dto.NodeDataDTO;
import com.gientech.ragcommon.graph.entity.NodeData;
import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;

import java.util.List;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2023/3/28 18:02
 */
@Mapper
public interface NodeDataDTOConvertor {
    NodeDataDTOConvertor INSTANCE = Mappers.getMapper(NodeDataDTOConvertor.class);

    List<NodeDataDTO> nodeDataList2NodeDataDTOList(List<NodeData> nodeDataList);
}
