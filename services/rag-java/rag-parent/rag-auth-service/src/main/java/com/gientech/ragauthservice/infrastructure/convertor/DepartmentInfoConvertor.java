package com.gientech.ragauthservice.infrastructure.convertor;

import com.gientech.ragauthservice.domain.entity.DepartmentInfo;
import com.gientech.ragauthservice.domain.model.DepartmentInfoDO;
import com.gientech.ragcommon.auth.dto.DeptImportExportDTO;
import com.gientech.ragcommon.auth.dto.FrameElement;
import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;

import java.util.ArrayList;
import java.util.LinkedList;
import java.util.List;

@Mapper
public interface DepartmentInfoConvertor {
    DepartmentInfoConvertor INSTANCE = Mappers.getMapper(DepartmentInfoConvertor.class);

    default List<FrameElement> departmentInfos2FrameElements(List<DepartmentInfo> departmentInfos) {
        if (departmentInfos == null) {
            return null;
        }

        List<FrameElement> list = new ArrayList<FrameElement>(departmentInfos.size());
        for (DepartmentInfo departmentInfo : departmentInfos) {
            list.add(departmentInfos2FrameElement(departmentInfo));
        }

        return list;
    }

    default FrameElement departmentInfos2FrameElement(DepartmentInfo departmentInfo) {
        if (departmentInfo == null) {
            return null;
        }

        FrameElement.FrameElementBuilder frameElement = FrameElement.builder();

        frameElement.id(departmentInfo.getId());
        frameElement.name(departmentInfo.getName());
        frameElement.parentId(departmentInfo.getParentId());

        return frameElement.build();
    }

    List<DeptImportExportDTO> frameElements2DeptImportExportDTOs(List<FrameElement> frameElements);

    default LinkedList<DepartmentInfo> departmentInfoDOs2DepartmentInfos(LinkedList<DepartmentInfoDO> departmentInfoDOS) {
        if ( departmentInfoDOS == null ) {
            return null;
        }

        LinkedList<DepartmentInfo> linkedList = new LinkedList<DepartmentInfo>();
        for ( DepartmentInfoDO departmentInfoDO : departmentInfoDOS ) {
            linkedList.add( departmentInfoDO2DepartmentInfo( departmentInfoDO ) );
        }

        return linkedList;
    }

    default DepartmentInfo departmentInfoDO2DepartmentInfo(DepartmentInfoDO departmentInfoDO) {
        if ( departmentInfoDO == null ) {
            return null;
        }

        DepartmentInfo departmentInfo = new DepartmentInfo();

        departmentInfo.setId( departmentInfoDO.getId() );
        departmentInfo.setName( departmentInfoDO.getName() );
        departmentInfo.setCode( departmentInfoDO.getCode() );
        departmentInfo.setAdmin( departmentInfoDO.getAdmin() );
        departmentInfo.setParentId( departmentInfoDO.getParentId() );
        departmentInfo.setStatus( departmentInfoDO.getStatus() );
        departmentInfo.setGmtCreate( departmentInfoDO.getGmtCreate() );
        departmentInfo.setGmtModified( departmentInfoDO.getGmtModified() );
        departmentInfo.setCreateBy( departmentInfoDO.getCreateBy() );
        departmentInfo.setModifyBy( departmentInfoDO.getModifyBy() );

        return departmentInfo;
    }
}

