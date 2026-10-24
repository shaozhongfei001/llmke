import { SearchOutlined } from "@ant-design/icons";
import { useMyHttpClient } from "@root/src/apis/api/index.js";
import { Api } from "@root/src/apis/api/Api";
import { Button, Checkbox, Input, message, Radio } from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";

export const AddFileContent = ({
  drawConfig,
  handleEvent,
  btnLoading,
  isFaq
}: {
  drawConfig: { type: string; data: any };
  handleEvent: (type: string, data?: any, cb?: (arg?: any) => void) => void;
  btnLoading: boolean;
  isFaq: boolean;
}) => {
  const api = new Api(useMyHttpClient());
  const { id: kbId }: any = useParams();
  const [list, setList] = useState([
    {
      id: 0,
      kbId: 0,
      fileName: "string",
      fileSize: 0,
      size: "string",
      filePath: "string",
      fullTextPath: "string",
      convertedFilePath: "string",
      status: 0,
      isEnable: 0,
      parseType: 0,
      chunkSize: 0,
      fileType: "string",
      embeddingModelName: "string",
      parsedFilePath: "string",
      faqExtractStatus: 0,
      reviseDate: "string",
      parentFileName: "string",
      version: "string",
      folderId: 0,
      folderName: "string",
      sourceUrl: "string",
      synLogs: [
        {
          id: 0,
          kbId: 0,
          targetId: 0,
          logType: 0,
          errorCode: "string",
          errorMessage: "string",
          errorDetail: "string"
        }
      ],
      kbFiles: ["string"],
      isFolder: 0,
      imagePaths: ["string"],
      pdfPage: 0,
      nodeCount: 0,
      edgeCount: 0,
      uid: "string",
      graphParseStatus: 0,
      "上传状态--解决上传失败信息太少": 0,
      "上传结果信息--解决上传失败信息太少": "string",
      "index--和公文对齐": 0,
      chunking: true,
      permission: 0,
      kbName: "string",
      elementType: 0,
      parentId: 0,
      fullFolderPath: "string",
      uploadTime: "2025-04-03T02:24:51.231Z",
      aqCount: 0
    }
  ]);
  const [value, setValue] = useState([]);
  const [searchInput, setSearchInput] = useState("");

  const getScatterListFn = async () => {
    try {
      const res: any = await api.getScatterList({
        kbId,
        fileListType: isFaq ? 2 : 1
      });
      if (res.success) {
        setList(res.data);
      }
    } catch (error) {
      console.log("====================================");
      console.log("error", error);
      console.log("====================================");
    }
  };

  const filterList = useMemo(() => {
    if (!searchInput) return list;
    return list.filter((item: any) => {
      const _fileName =
        item?.fileName && typeof item.fileName === "string"
          ? item.fileName
          : "";
      const _searchInput =
        searchInput && typeof searchInput === "string" ? searchInput : "";
      return _fileName.toLowerCase().includes(_searchInput.toLowerCase());
    });
  }, [list, searchInput]);

  useEffect(() => {
    getScatterListFn();
  }, []);

  return (
    <div className="w-full h-full pt-[12px]">
      <div className="h-[calc(100%-80px)]">
        <div className="box-border border-solid border-[1px] border-[#D9D9D9] h-full overflow-y-auto rounded-[4px] p-[16px]">
          <Input
            placeholder="搜索文件名"
            suffix={<SearchOutlined onClick={() => {}} />}
            value={searchInput}
            onChange={(e: any) => setSearchInput(e?.target?.value || "")}
            className="mb-[10px]"
          />
          <div className="h-[calc(100%-56px)] overflow-y-auto overflow-x-hidden mt-[12px]">
            <Checkbox.Group
              value={value}
              onChange={(checkedValue: any) => {
                setValue(checkedValue);
              }}
            >
              {filterList.map((item: any) => {
                return (
                  <Checkbox value={item.id} className="my-[8px] w-full">
                    {item.fileName}
                  </Checkbox>
                );
              })}
            </Checkbox.Group>
          </div>
        </div>
      </div>
      <div className="h-[20px] w-[5px]"></div>
      <div
        className="flex justify-end h-[38px] pt-[16px]"
        style={{ borderTop: "1px solid #EBEBEB" }}
      >
        <Button
          style={{
            border: "1px solid #EBEBEB",
            color: "#555555",
            marginRight: "16px"
          }}
          onClick={() => {
            handleEvent("closeDrawer");
          }}
        >
          取消
        </Button>
        <Button
          style={{
            border: "none",
            color: "#fff",
            background:
              "linear-gradient(99.9deg, #2b69ff -4.18%, #8f91ff 106.52%)"
          }}
          loading={btnLoading}
          onClick={() => {
            if (!value.length) return message.warning("请选择");
            const fileIds = Array.isArray(drawConfig.data)
              ? drawConfig.data.map((item: any) => item.id)
              : [drawConfig.data.id];
            handleEvent("save:addFile", {
              kbId,
              fileIds: value,
              parentFileName: drawConfig.data.parentFileName,
              groupId: drawConfig.data.groupId
            });
          }}
        >
          确认
        </Button>
      </div>
    </div>
  );
};
export default AddFileContent;
