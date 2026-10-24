import {
  DownloadOutlined,
  PlusCircleOutlined,
  SearchOutlined
} from "@ant-design/icons";
import { Button, Dropdown, Flex, Input, Spin, Typography } from "antd";
import back from "../../../../assets/img/back.png";
import grayWarning from "../../../../assets/img/grayWarning.png";
import AutoTag from "./common/components/autoTag";
import { useSensitiveDetailController } from "./common/useSensitiveDetailController";
import UploadModal from "@root/src/components/UploadModal";
import axios$ from "@root/src/apis";
import { useNavigate } from "react-router-dom";
import { getUrlPrefix, useAppPassport } from "@root/src/core/helps";
import { useRef } from "react";

const SensitiveDetail = () => {
  const navigator = useNavigate();
  const { getToken } = useAppPassport();
  const tagsWrapRef = useRef(null);

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
      // const _link = document.createElement("a");
      // const _body = document.body;
      // _link.href = filePath;
      // //_link.download = fileName;

      // _link.style.display = "none";
      // _body.appendChild(_link);

      // const event = new MouseEvent("click", {
      //   view: window,
      //   bubbles: true,
      //   cancelable: true
      // });
      // _link.dispatchEvent(event);
      // // _link.click()
      // setTimeout(() => {
      //   _body.removeChild(_link);
      // }, 100);
    } else {
      //console.log("缺少文件名或文件地址：", file);
    }
  };
  const goBack = () => {
    navigator(-1);
  };
  const tableProps: any = useSensitiveDetailController();
  return (
    <>
      <div className="h-full px-[16px] py-[16px]">
        <div className="flex items-center justify-between pt-[4px] pb-[20px]">
          <div className="flex items-center">
            {/* <div className="w-[4px] h-[12px] rounded-[2px] bg-[#014DDF] mr-[3px]"></div> */}
            <img src={back} className="cursor-pointer" onClick={goBack} />
            <div className="ml-[30px] text-[16px] text-[#1D2129] bold">
              {tableProps?.detailData?.name}
            </div>
          </div>
        </div>
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
                  `${getUrlPrefix()}/sensitive/word/downloadTemplate?fileType=${e.target.innerText}`,
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
