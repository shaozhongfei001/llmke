import { Flex, Modal, Tooltip, message, Button, Tag } from "antd";
import { EllipsisOutlined } from "@ant-design/icons";
import { useState } from "react";
import { useServices } from "@/components/KnowledgeBaseZh/service.ts";
// import "@/assets/styles/knowledgebase.less";
import { FILE_BTN, getBtnDisabled } from "@root/src/const/permission";
import { formatFileSize } from "@root/src/core/helps";

interface ICard {
  row: {
    id: number;
    kbName: string;
    kbDes: string | any;
    kbLabel: string | any;
    fileCount: number;
    fileTotalSize: number;
    permission: number;
  };
  fetchList: (str?: string) => void;
  reNameHandler?: (row: any) => void;
  goToDetail: (row: any) => void;
  //写作流程从素材库选择
  cancelHover?: boolean;
  clickCardItem?: (item: any) => any;
  doubleClickCardItem?: (cardItem: any) => any;
  isSelected?: boolean;
}

const KnowledgeBaseCard = (props: ICard) => {
  const {
    row,
    fetchList,
    reNameHandler,
    goToDetail,
    clickCardItem,
    isSelected = false
  } = props;
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const { deleteKbById } = useServices();

  const handleCardClick = (e: React.MouseEvent<HTMLDivElement, MouseEvent>) => {
    if (clickCardItem) {
      clickCardItem(row);
      return;
    }
    e.stopPropagation();
    goToDetail(row);
  };

  const deleteKB = (e: React.MouseEvent<HTMLDivElement, MouseEvent>) => {
    e.stopPropagation();
    if (getBtnDisabled(FILE_BTN.DELETE, row.permission)) return;
    setShowConfirmModal(true);
  };

  const renameKB = (e: React.MouseEvent<HTMLDivElement, MouseEvent>) => {
    e.stopPropagation();
    if (getBtnDisabled(FILE_BTN.EDIT, row.permission)) return;
    reNameHandler && reNameHandler({ ...row });
  };

  const confirmDeleteKB = () => {
    const { id } = row;
    if (id) {
      setLoading(true);
      deleteKbById(id)
        .then(() => {
          setShowConfirmModal(false);
          setLoading(false);
          fetchList();
          message.success("知识库删除成功");
        })
        .catch((e) => {
          console.log(e);
          setLoading(false);
        });
    }
  };

  const renderTagList = (label: string) => {
    const tags = label.split(";");
    const renderTags = tags.slice(0, 3);
    if (tags.length > 3) renderTags.push("...");

    const renderFullList = () => {
      return (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 10,
            padding: 15
          }}
        >
          {tags.slice(3, tags.length).map((str: any, index: any) => (
            <Tag color="blue" title={str} key={index}>
              {str}
            </Tag>
          ))}
        </div>
      );
    };
    return renderTags.map((str: string, index: any) => {
      if (str == "...") {
        return (
          <Tooltip title={renderFullList()} key={index} color="#fff">
            <Tag color="blue" key={index}>
              {str}
            </Tag>
          </Tooltip>
        );
      }
      return (
        <Tag color="blue" key={index}>
          {str}
        </Tag>
      );
    });
  };

  return (
    <>
      <div
        className="card-wrap"
        onClick={handleCardClick}
        style={{
          border: isSelected ? "1px solid #055aff" : ""
        }}
      >
        <div className="flex w-full justify-start  items-start">
          <div className="knowledge-icon"></div>
          <div
            className="knowledge-name h-auto! line-clamp-2 "
            title={row.kbName}
          >
            {row.kbName}
          </div>
        </div>

        <span>
          {/* <div className="knowledge-tags">
            {row.kbLabel && renderTagList(row.kbLabel)}
            {!row.kbLabel && "暂无标签"}
          </div> */}
          <div className="flex absolute bottom-0 left-0 w-full px-5 pb-2 justify-between">
            <div className="knowledge-info">
              <label
                title={
                  typeof row?.fileCount === "number"
                    ? row?.fileCount.toString()
                    : "-"
                }
              >
                文件数：
              </label>
              <label
                style={{
                  color: "#555"
                }}
              >
                {typeof row?.fileCount === "number" ? row?.fileCount : "-"}
              </label>
              <span>·</span>
              <label
                title={
                  typeof row?.fileTotalSize === "number"
                    ? row?.fileTotalSize.toString()
                    : "-"
                }
              >
                大小：
              </label>
              <label
                style={{
                  color: "#555"
                }}
              >
                {formatFileSize(row?.fileTotalSize)}
              </label>
            </div>
            <Tooltip
              className="inline-block"
              placement="right"
              arrow={false}
              overlayInnerStyle={{
                padding: 0
              }}
              title={
                <div className="w-[68px] text-center leading-[32px] cursor-pointer">
                  <div
                    className={` ${getBtnDisabled(FILE_BTN.EDIT, row.permission) ? "cursor-not-allowed text-text-color3" : "cursor-default text-[#555555]"} card-hover-operations-item hover:bg-[#F1F5FF]`}
                    onClick={renameKB}
                  >
                    编辑
                  </div>
                  <div
                    className={`${getBtnDisabled(FILE_BTN.DELETE, row.permission) ? "cursor-not-allowed text-text-color3" : "cursor-default text-[#555555]"} card-hover-operations-item `}
                    onClick={deleteKB}
                  >
                    删除
                  </div>
                </div>
              }
              color={"#fff"}
            >
              <EllipsisOutlined className="hover:bg-[#F1F5FF] hover:text-[#055AFF]" />
            </Tooltip>
          </div>
        </span>
      </div>
      <Modal
        closable={false}
        className="delete-modal"
        open={showConfirmModal}
        title="是否确定删除该知识库吗，删除后将不可恢复?"
        onCancel={() => setShowConfirmModal(false)}
        onOk={confirmDeleteKB}
        confirmLoading={loading}
      ></Modal>
    </>
  );
};

export default KnowledgeBaseCard;
