package com.gientech.ragcommon.graph.convertor;

import com.gientech.ragcommon.graph.dto.GraphDataDTO;
import com.gientech.ragcommon.graph.entity.GraphData;
import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;

@Mapper
public interface GraphDataDTOConvertor {

    GraphDataDTOConvertor INSTANCE = Mappers.getMapper(GraphDataDTOConvertor.class);

    /**
     * 图数据实体转换为图数据DTO
     *
     * @param graphData
     * @return
     */
    GraphDataDTO graphData2GraphDataDTO(GraphData graphData);

    /**
     * 节点实体转换为节点DTO
     *
     * @param nodeData
     * @return
     */
//    NodeDataDTO nodeData2NodeDataDTO(NodeData nodeData);

    /**
     * 边实体转换为边DTO
     *
     * @param edgeData
     * @return
     */
//    EdgeDataDTO edgeData2EdgeDataDTO(EdgeData edgeData);

    /**
     * 属性实体转换为属性DTO
     *
     * @param property
     * @return
     */
//    PropertyDTO property2PropertyDTO(@Param("property") Property property);
}
