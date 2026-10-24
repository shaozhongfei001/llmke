package com.gientech.ragqaservice.domain.conventer;

import com.gientech.ragcommon.qa.dto.SearchConfigDTO;
import com.gientech.ragcommon.qa.entity.Config;
import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;

/**
 * @Descrption:
 * @Author:liutaiyun
 * @Date:2024/07/23 14:02
 **/
@Mapper
public interface SearchConfigConvertor {

    SearchConfigConvertor INSTANCE = Mappers.getMapper(SearchConfigConvertor.class);

    Config searchConfigDTOToSearchConfig(SearchConfigDTO searchConfigDTO);

    SearchConfigDTO searchConfigToSearchConfigDto(Config config);

}
