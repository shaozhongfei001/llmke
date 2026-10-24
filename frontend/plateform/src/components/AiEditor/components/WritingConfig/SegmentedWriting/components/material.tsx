import { useMemo } from "react";
import { v4 as uuid } from "uuid";
import { Popover } from "antd";

import RenderMaterialList from "./materialList";
interface MaterialItemType {
  id: number;
  fileName: string;
  state: number;
  material_type: number[];
}

interface MaterialType {
  id: number;
  name: string;
  parentID: number;
  gmtCreate: string;
  subTypeList?: MaterialType[];
}
const RenderMaterialType = ({
  materialTypes,
  materialList,
  deleteMertial,
  retryParse,
  reUpload
}: any) => {
  const findMaterialItemById = (id: number) => {
    let type: any;
    const traverse = (materialType: MaterialType[]) => {
      materialType.some((m: MaterialType) => {
        if (m.id == id) {
          type = m;
          return true;
        }
        if (m.subTypeList) {
          traverse(m.subTypeList);
        }
      });
    };
    traverse(materialTypes);
    return type;
  };
  // 素材列表根据上传类型分类, 用于展示素材列表
  const materialByUploadType = useMemo(() => {
    console.log("materialByUploadType", materialTypes, materialList);
    if (materialList?.length > 0 && materialTypes?.length > 0) {
      const categorized: any = {};
      materialList.forEach((file: any) => {
        (file.material_type || []).forEach((type: number) => {
          const typeItem = findMaterialItemById(type);
          if (typeItem) {
            const typeLabel = (typeItem || {}).name;
            if (!categorized[typeLabel]) {
              categorized[typeLabel] = [];
            }
            categorized[typeLabel].push({
              ...file
            });
          }
        });
      });
      return categorized;
    }
    return undefined;
  }, [materialList, materialTypes]);

  return (
    materialByUploadType &&
    Object.keys(materialByUploadType).map((type) => {
      return (
        <Popover
          content={
            <RenderMaterialList
              list={materialByUploadType[type]}
              deleteMertial={deleteMertial}
              retryParse={retryParse}
              reUpload={reUpload}
            />
          }
          trigger="hover"
          key={uuid()}
        >
          <div className="px-[8px] h-[32px] border-[1px] border-[#EEEEEE] border-solid text-center leading-[32px]">
            {type}
            <div className="text-[#055AFF] ml-[8px] inline-block">
              {materialByUploadType[type]?.length}
            </div>
          </div>
        </Popover>
      );
    })
  );
};

export default RenderMaterialType;
