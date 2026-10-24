import { Flex, Modal, Tooltip, message, Button, Tag } from "antd";
import { DeleteOutlined, EditOutlined, TeamOutlined } from "@ant-design/icons";
import { useState } from "react";
import { useServices } from "../service";
import "@/assets/styles/knowledgebase.less";
import {
  FILE_BTN,
  getBtnDisabled,
  PERMISSION_RULES,
  PERMISSION_STATUS
} from "@root/src/const/permission";

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

const Card = (props: ICard) => {
  const {
    row,
    fetchList,
    reNameHandler,
    goToDetail,
    cancelHover,
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

  const configKB = (e: React.MouseEvent<HTMLDivElement, MouseEvent>) => {
    e.stopPropagation();
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
        <div className="knowledge-icon"></div>
        <span>
          <div className="knowledge-name" title={row.kbName}>
            {row.kbName}
          </div>
          {/* <div className="knowledge-des" title={row.kbDes}>
            {row.kbDes || "无描述"}
          </div> */}
          <div className="knowledge-tags">
            {row.kbLabel && renderTagList(row.kbLabel)}
            {!row.kbLabel && "暂无标签"}
          </div>
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
          {/* <div className="tooltip-wrap">
            <Tooltip
              className="a"
              title={renderOperations}
              color="#fff"
              placement="bottom"
            >
              ...
            </Tooltip>
          </div> */}
        </span>
        {!cancelHover && (
          <Flex className="card-hover-operations" align="center">
            <div
              onClick={deleteKB}
              className={`${getBtnDisabled(FILE_BTN.DELETE, row.permission) ? "cursor-not-allowed text-text-color3" : "cursor-default text-primary-color"} card-hover-operations-item `}
            >
              删除
            </div>
            <span
              style={{
                height: "18px",
                width: "1px",
                backgroundColor: "#E8E8E8"
              }}
            ></span>
            <div
              className={` ${getBtnDisabled(FILE_BTN.EDIT, row.permission) ? "cursor-not-allowed text-text-color3" : "cursor-default text-primary-color"} card-hover-operations-item`}
              onClick={renameKB}
            >
              编辑
            </div>
          </Flex>
        )}
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

export default Card;
