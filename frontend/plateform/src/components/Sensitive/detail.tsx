import {
  DownloadOutlined,
  PlusCircleOutlined,
  SearchOutlined
} from "@ant-design/icons";
import { Button, Dropdown, Flex, Input, Spin, Typography } from "antd";
import back from "@/assets/img/back.png";
import grayWarning from "@/assets/img/grayWarning.png";
import AutoTag from "./components/autoTag";
import UploadModal from "@root/src/components/UploadModal";
import axios$ from "@root/src/apis";
import { useNavigate } from "react-router-dom";
import { useAppPassport } from "@root/src/core/helps";
import { useRef } from "react";
import { useSensitiveDetailController } from "./useSensitiveDetailController";

const SensitiveDetail = () => {
  const navigator = useNavigate();
  const { getToken } = useAppPassport();
  const tagsWrapRef = useRef(null);

  const tableProps: any = useSensitiveDetailController();

  const handleDownload = async (filePath: string, fileType: string) => {
    const token = getToken();
    if (filePath) {
      const res: any = await axios$.get(filePath, {
        responseType: "blob",
        headers: {
          Authorization: token
        }
      });
      if (res) {
        const href = URL.createObjectURL(res);
        const box = document.createElement("a");
        box.href = href;
        box.download = `模板文件.${fileType}`;
        box.click();
      }
    } else {
      //console.log("缺少文件名或文件地址：", file);
    }
  };
  const goBack = () => {
    navigator(-1);
  };

  return (
    <>
      <div className="h-full px-[16px]">
        <Flex justify="flex-start" align="center" className="mb-4">
          <div className="flex items-center">
            <img src={back} className="cursor-pointer mr-2 " onClick={goBack} />
            <b className="text-[16px] text-[#2A2A2A] bold ml-[16px]">
              {tableProps?.detailData?.name}
            </b>
          </div>
        </Flex>
        <div className="px-[20px] pt-[20px] h-[calc(100%-77px)] rounded-[8px] bg-white">
          <Flex justify="space-between">
            <Flex>
              <Button
                type="primary"
                icon={<PlusCircleOutlined />}
                className="w-[82px] border-none"
                style={{ background: "linear-gradient(90deg,#075BFF,#AC96FF)" }}
                onClick={() => {
                  tableProps.handleEvent("upload");
                }}
              >
                导入
              </Button>
              <div className="ml-[16px] text-[12px] text-text-color2 flex items-center">
                <img src={grayWarning} className=" mr-[4px]" />
                <div>敏感词最多可输入16个字符</div>
              </div>
            </Flex>
            <Input
              // allowClear
              value={tableProps.fuzzyNameOrId}
              placeholder="请输入内容"
              style={{ width: "240px" }}
              suffix={
                <SearchOutlined
                  style={{ color: "#999", fontSize: 12 }}
                  onClick={() => tableProps.handleEvent("clickForSearch")}
                />
              }
              onChange={tableProps.fuzzyNameOrIdOnChange}
              onKeyDown={tableProps.handleKeyDown}
            />
          </Flex>
          <div
            ref={tagsWrapRef}
            className="overflow-hidden border-[1px] h-[calc(100%-120px)] border-solid border-[#D9D9D9] py-4 pl-4 pr-1 bg-[#F5F5F5] mt-4 rounded-lg"
          >
            <AutoTag
              wrapRef={tagsWrapRef}
              tags={tableProps.tags}
              setTags={tableProps.setTags}
              fuzzyNameOrId={tableProps.filter}
            />
          </div>
          <div className="h-[72px] flex items-center justify-end">
            <Button
              style={{ width: "76px" }}
              className="mr-[16px] border-[#EBEBEB]"
              onClick={goBack}
            >
              取消
            </Button>
            <Button
              type="primary"
              style={{
                background: "linear-gradient(90deg,#075BFF,#AC96FF)",
                width: "76px",
                border: "none"
              }}
              onClick={() => {
                tableProps.handleEvent("update");
              }}
            >
              保存
            </Button>
          </div>
        </div>
        {tableProps.loading && (
          <div className="absolute top-0 left-0 w-full h-full flex justify-center items-center bg-[rgba(255,255,255,.3)]">
            <Spin size="large" spinning={tableProps.loading}></Spin>
          </div>
        )}
      </div>{" "}
      <UploadModal
        isShowCreateModal={tableProps.showUploadModal}
        closeModal={tableProps.setShowUploadModal}
        uploadEvents={tableProps.handleEvent}
        multiple={false}
        url={`/sensitive/word/${tableProps.sensitiveId}/import`}
      >
        <Dropdown
          menu={{
            items: [
              {
                key: "csv",
                label: "csv"
              },
              {
                key: "txt",
                label: "txt"
              }
            ]
          }}
          dropdownRender={(menu) => (
            <div
              onClick={(e: any) => {
                e.stopPropagation();
                //downLoadTemplate(e.target.innerText);
                handleDownload(
                  `/proxy/sensitive/word/downloadTemplate?fileType=${e.target.innerText}`,
                  e.target.innerText
                );
              }}
            >
              {menu}
            </div>
          )}
          placement="bottom"
        >
          <Button
            className="border-[#EBEBEB] text-primary-color bg-white"
            onClick={(e) => {
              e.stopPropagation();
            }}
          >
            下载模板
          </Button>
        </Dropdown>
      </UploadModal>
    </>
  );
};

export default SensitiveDetail;
