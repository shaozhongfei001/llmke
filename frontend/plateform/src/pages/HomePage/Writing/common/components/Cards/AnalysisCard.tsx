import { useState, useCallback, useRef } from "react";
import { Tooltip } from "antd";
import { EllipsisOutlined } from "@ant-design/icons";
import AnalysisIcon from "@/assets/img/analysis.png";
import DeleteConfirm from "@/pages/HomePage/Writing/common/components/DeleteModal";
import { useServices } from "@/pages/HomePage/Writing/Module/common/server.ts";
import { IAnalysis } from "../../../Module/common/type";
interface Iprops {
  detail: IAnalysis;
  deleteNode: (id: string) => void;
  duplicateNode: (id: string) => void;
  goDetail: (id: string) => void;
  renameNode: (id: string, name: string) => void;
}
const AnalysisCard = ({
  detail,
  deleteNode,
  duplicateNode,
  goDetail,
  renameNode
}: Iprops) => {
  const [isShowDeleteModal, setIsShowDeleteModal] = useState<boolean>(false);

  const { deleteAnalysis } = useServices();
  const cancelDelete = (state: boolean) => {
    setIsShowDeleteModal(state);
  };

  // 渲染卡片操作菜单
  const renderMenu = useCallback(
    (node: IAnalysis) => {
      return (
        <>
          <div
            className="text-[#555555] hover:bg-[#F1F5FF] pl-[16px]"
            onClick={(e) => {
              e.stopPropagation();
              renameNode(node.id, node.name);
            }}
          >
            重命名
          </div>
          {node.name !== "未命名组件" && (
            <div
              className="text-[#555555] hover:bg-[#F1F5FF] pl-[16px]"
              onClick={(e) => {
                e.stopPropagation();
                duplicateNode(node.id);
              }}
            >
              复制
            </div>
          )}
          <div
            className="text-[#555555] hover:bg-[#F1F5FF] pl-[16px]"
            onClick={(e) => {
              e.stopPropagation();
              setIsShowDeleteModal(true);
            }}
          >
            删除
          </div>
        </>
      );
    },
    [duplicateNode]
  );

  const renderTitleColor = (text: string) => {
    if (text == "未命名组件") {
      return "#FF3A3A";
    }
    return "#2A2A2A";
  };

  return (
    <>
      <DeleteConfirm
        isShowDeleteModal={isShowDeleteModal}
        closeModal={cancelDelete}
        confirmModal={() => deleteNode(detail.id)}
        loading={deleteAnalysis.isLoading}
      />
      {detail && (
        <div
          className="w-[306px] h-[114px] p-[16px] flex flex-col justify-between rounded-lg relative border-[1px] border-solid border-[#EEEEEE] hover:border-[#055AFF]"
          onClick={() => goDetail(detail.id)}
        >
          {detail.state == 0 && (
            <div
              style={{
                background: "linear-gradient(180deg, #ECECFF 0%, #F2F2FF 100%)"
              }}
              className="absolute top-0 right-0 rounded-tr-lg rounded-bl-lg px-2 py-[2px] text-[#055AFF]"
            >
              编辑中
            </div>
          )}
          <div className=" flex font-bold text-[16px]">
            <img src={AnalysisIcon} width={48} className="mr-3" />
            <div
              className="break-words text-ellipsis  line-clamp-1"
              style={{
                color: renderTitleColor(detail.name)
              }}
            >
              {detail.name}
            </div>
          </div>

          <div className="flex align-middle w-[calc(100%-26px)]">
            <div className="text-[#888] min-w-[42px]">描述：</div>
            <div className="truncate text-[#555555]">
              {detail?.description || "--"}
            </div>
          </div>

          <Tooltip
            className="inline-block absolute right-[8px] bottom-[8px]"
            placement="right"
            arrow={false}
            overlayInnerStyle={{
              padding: 0
            }}
            title={
              <div className="w-[68px] text-left leading-[32px] cursor-pointer">
                {renderMenu(detail)}
              </div>
            }
            color={"#fff"}
          >
            <EllipsisOutlined
              className="hover:bg-[#F1F5FF] hover:text-[#055AFF] cursor-pointer h-6 px-1 text-base rounded pt-[2px]"
              onClick={(e) => e.stopPropagation()}
            />
          </Tooltip>
        </div>
      )}
    </>
  );
};

export default AnalysisCard;
