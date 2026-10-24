import React, { useRef } from "react";
import { Button, Divider, Typography } from "antd";
import { useHover } from "ahooks";
const { Text, Title, Paragraph } = Typography;
import { EditOutlined, DeleteOutlined, FolderFilled } from "@ant-design/icons";
import dayjs from "dayjs";

export interface FileProps {
  edit: any;
  del: any;
  item: any;
  enter: any;
}

const FileCard: React.FC<FileProps> = (props) => {
  const { edit, del, item, enter } = props;
  const ref = useRef(null);
  const isHovering = useHover(ref);
  return (
    <div className="rounded bg-white relative" ref={ref}>
      <div className="flex flex-col rounded-lg text-center w-full h-full">
        <div
          onClick={() => enter(item)}
          className="cursor-pointer flex flex-col w-full items-center relative flex-grow py-5 px-2"
        >
          <div className=" w-[80%] py-3 relative cursor-pointer">
            <FolderFilled
              className={`text-[65px] ${
                isHovering ? "text-sky-500" : "text-slate-700"
              } transition-all duration-150 ease-in-out`}
            />
          </div>
          <div
            className={`w-full mx-auto flex flex-col items-center text-center ${
              isHovering ? " opacity-100" : " opacity-70"
            }  transition-all duration-150 ease-in-out`}
          >
            <Title level={5} ellipsis className="w-[80%]">
              {item?.kbName || "--"}
            </Title>
            <Paragraph
              type="secondary"
              ellipsis={{ rows: 3 }}
              className="w-[80%]"
            >
              {item?.kbDes || ""}
            </Paragraph>
          </div>
        </div>
        <div className="w-full pb-3 flex items-center">
          <Button
            onClick={() => edit(item)}
            icon={<EditOutlined />}
            type="text"
            block
          >
            编辑
          </Button>
          <Button
            danger
            onClick={() => del(item)}
            icon={<DeleteOutlined />}
            type="text"
            block
          >
            删除
          </Button>
          {/* <Divider type="vertical"/> */}
        </div>
      </div>
    </div>
  );
};

export default FileCard;
