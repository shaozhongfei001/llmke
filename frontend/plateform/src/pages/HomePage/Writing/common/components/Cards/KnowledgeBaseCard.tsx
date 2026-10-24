import { Flex, Modal, Tooltip, message, Button, Tag } from "antd";
import { EllipsisOutlined } from "@ant-design/icons";
import { useState } from "react";
import { useServices } from "@/components/KnowledgeBaseZh/service.ts";
import "@/assets/styles/knowledgebase.less";

interface ICard {
  row: {
    id: number;
    kbName: string;
    kbDes: string | any;
    kbLabel: string | any;
    fileCount: number;
    fileTotalSize: number;
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
    setShowConfirmModal(true);
  };

  const renameKB = (e: React.MouseEvent<HTMLDivElement, MouseEvent>) => {
    e.stopPropagation();
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
        <div className="knowledge-icon"></div>
        <span>
          <div className="knowledge-name" title={row.kbName}>
            {row.kbName}
          </div>
          <div className="knowledge-tags">
            {row.kbLabel && renderTagList(row.kbLabel)}
            {!row.kbLabel && "暂无标签"}
          </div>
          <div className="flex justify-between">
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
                {typeof row?.fileTotalSize === "number"
                  ? row?.fileTotalSize
                  : "-"}
                M
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
                    className="text-[#555555] hover:bg-[#F1F5FF] "
                    onClick={renameKB}
                  >
                    编辑
                  </div>
                  <div
                    className="text-[#555555] hover:bg-[#F1F5FF]"
                    onClick={deleteKB}
                  >
                    删除
                  </div>
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
