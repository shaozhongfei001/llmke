import { Flex } from "antd";
import ChooseMe from "@/components/AiEditor/assets/icon/chooseMe.svg";
import UpArrow from "@/components/AiEditor/assets/img/upArrow.png";
import DownArrow from "@/components/AiEditor/assets/img/downArrow.png";
import DeleteIcon from "@/components/AiEditor/assets/icon/deleteIcon.svg";
import { useState } from "react";
import { MaterialModal } from "../MaterialModal";

const MaterialList = ({
  confirmSelect,
  contentSources,
  curMaterialList,
  setCurMaterialList,
}) => {
  const [materialOpen, setMaterialOpen] = useState<boolean>(false);
  const [showMe, setShowMe] = useState(false);
  const closeMaterial = () => {
    setMaterialOpen(false);
  };
  const openMaterial = () => {
    setMaterialOpen(true);
  };
  return (
    <>
      <MaterialModal
        open={materialOpen}
        closeMaterial={closeMaterial}
        confirmSelect={confirmSelect}
        contentSources={contentSources}
        selectMaterialList={curMaterialList}
        setSelectMaterialList={setCurMaterialList}
      />
      <Flex className="w-full">
        <div className="w-full">
          <div className="flex mb-[8px] items-center">
            <div className="text-sm shrink-0 mr-[10px]">选择素材</div>
            <img
              src={ChooseMe}
              className={`cursor-pointer`}
              width={16}
              height={16}
              onClick={() => {
                openMaterial();
              }}
            />
          </div>
          <div className="bg-[#F0F0F0] rounded-[4px] px-[8px] py-[8px]">
            <div className="flex justify-between items-center cursor-pointer">
              <div className="text-[14px] text-[#222222]">
                {curMaterialList.length
                  ? `选择 ${curMaterialList.length} 篇文章作为素材`
                  : "暂无选择素材，素材为空的"}
              </div>
              {curMaterialList.length ? (
                <img
                  src={showMe ? UpArrow : DownArrow}
                  onClick={() => setShowMe(!showMe)}
                />
              ) : (
                <></>
              )}
            </div>
            {showMe && (
              <div>
                {(curMaterialList || []).map((item, index) => {
                  return (
                    <div
                      key={index}
                      className="text-[12px] text-[#055AFF] flex justify-between mt-[12px]"
                    >
                      <div className="w-[360px] line-clamp-1 overflow-ellipsis break-words ">
                        {index + 1}. {item.fileName}
                      </div>
                      <img
                        src={DeleteIcon}
                        width={16}
                        height={16}
                        className="cursor-pointer"
                        onClick={() => {
                          const rest = curMaterialList.filter(
                            (v) => v.id !== item.id
                          );
                          setCurMaterialList([...rest]);
                        }}
                      />
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </Flex>
    </>
  );
};

export default MaterialList;
