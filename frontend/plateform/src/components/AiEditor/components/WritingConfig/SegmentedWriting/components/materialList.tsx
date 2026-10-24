import { useCallback, useState, useMemo, useEffect, useRef } from "react";
import { v4 as uuid, validate } from "uuid";
import {
  Button,
  Flex,
  Form,
  Select,
  Popover,
  message,
  Modal,
  Table
} from "antd";
import w2 from "@/assets/img/w2.png";
import w1 from "@/assets/img/w1.png";
import database from "@/assets/img/database.png";
import File from "@/assets/img/File.png";
import vertor from "@/assets/img/vector.png";
import close from "@/assets/img/CloseCircle.png";
import genera from "@/assets/gif/genera.gif";
import redFile from "@/assets/img/redFile.png";
import isDelete from "@root/src/assets/img/isDelete.png";
interface MaterialItemType {
  id: number;
  fileName: string;
  state: number;
  material_type: number[];
}

const RenderMaterialList = ({
  list,
  deleteMertial,
  retryParse,
  reUpload
}: any) => {
  const [materialIdHover, setMaterialIdHover] = useState<number>();

  const renderMaterialStatus = useCallback(
    (li: MaterialItemType) => {
      switch (li.state) {
        case 2: //解析中
          return (
            <>
              <div className={`w-[400px] truncate text-[#2A2A2A]`}>
                <img src={File} width={14} height={14} />
                <span className="ml-[4px]">{li.fileName}</span>
              </div>
              <div className="w-[80px] flex justify-end items-center">
                {materialIdHover == li.id ? (
                  <img
                    src={close}
                    width={14}
                    height={14}
                    onClick={() => deleteMertial(li.id)}
                  />
                ) : (
                  <>
                    <img
                      src={genera}
                      width={16}
                      height={16}
                      className="mr-[6px]"
                    />
                    <span className="text-[#055AFF]  cursor-pointer">
                      解析中
                    </span>
                  </>
                )}
              </div>
            </>
          );
        case 3:
          return (
            <>
              <div className={`w-[400px] truncate text-[#2A2A2A]`}>
                <img src={File} width={14} height={14} />
                <span className="ml-[4px]">{li.fileName}</span>
              </div>
              <div className="w-[80px] flex justify-end items-center">
                {materialIdHover == li.id ? (
                  <img
                    src={close}
                    width={14}
                    height={14}
                    onClick={() => deleteMertial(li.id)}
                  />
                ) : (
                  <img src={vertor} width={14} height={14} />
                )}
              </div>
            </>
          );
        case 4: //解析失败
          return (
            <>
              <div className={`w-[400px] truncate text-[#FF4D4F]`}>
                <img src={redFile} width={14} height={14} />
                <span className="ml-[4px]">{li.fileName}</span>
              </div>
              <div className="w-[80px] flex justify-end items-center">
                {materialIdHover == li.id ? (
                  <>
                    <span
                      className="text-[#055AFF] cursor-pointer mr-[6px]"
                      onClick={() => retryParse(li.id)}
                    >
                      重新解析
                    </span>
                    <img
                      src={close}
                      width={14}
                      height={14}
                      onClick={() => deleteMertial(li.id)}
                    />
                  </>
                ) : (
                  <span className="text-[#FF4D4F]  cursor-pointer">
                    解析失败
                  </span>
                )}
              </div>
            </>
          );
        case 6: //丢失
          return (
            <>
              <div className={`w-[400px] truncate text-[#BBBBBB] line-through`}>
                <img src={isDelete} width={14} height={14} />
                <span className="ml-[4px]">{li.fileName}</span>
              </div>
              <div className="w-[80px] flex justify-end items-center">
                {materialIdHover == li.id ? (
                  <>
                    <span
                      className="text-[#055AFF] cursor-pointer mr-[6px]"
                      onClick={() => reUpload()}
                    >
                      重新上传
                    </span>
                    <img
                      src={close}
                      width={14}
                      height={14}
                      onClick={() => deleteMertial(li.id)}
                    />
                  </>
                ) : (
                  <span className="text-[#BBBBBB] cursor-pointer">丢失</span>
                )}
              </div>
            </>
          );
      }
    },
    [materialIdHover]
  );
  return list.map((li: MaterialItemType) => {
    return (
      <Flex
        justify="space-between"
        align="center"
        className="h-[32px] w-[560px]"
        onMouseEnter={(e) => {
          e.stopPropagation();
          setMaterialIdHover(li.id);
        }}
        onMouseLeave={(e) => {
          e.stopPropagation();
          setMaterialIdHover(undefined);
        }}
        key={li.id}
      >
        {renderMaterialStatus(li)}
      </Flex>
    );
  });
};
export default RenderMaterialList;
