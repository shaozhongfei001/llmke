import React from "react";
import { Button, Dropdown, Flex, Modal } from "antd";
import { CloseOutlined } from "@ant-design/icons";
import { ReactComponent as AiBoy } from "@/assets/svg/aiBoy.svg";
import { ReactComponent as ListSvg } from "@/assets/svg/list.svg";
import { ReactComponent as ListClickSvg } from "@/assets/svg/listClick.svg";

import useController from "./common/useController";
import Card from "../common/components/Cards/HomeCard";
import "./styles.less";
import TempPreview from "../TemplateM/components/TempPreview";
import DeleteConfirm from "../common/components/DeleteModal";
import { uniqueId } from "lodash";

function DocWriting() {
  const {
    docList,
    tempClassList,
    listDropDownShow,
    handleAction,
    handleFileChange,
    fileRefresh,
    tempPreview,
    tempPreviewClose,
    tempPreviewInfo,
    showDeleteModal,
    confirmModal,
    deleteTemplate,
    closeDeleteModal,
    onDocListOpenChange
  }: any = useController();

  return (
    <div className="w-full h-full overflow-y-auto overflow-x-hidden flex flex-col items-center relative newIndex">
      <DeleteConfirm
        isShowDeleteModal={showDeleteModal}
        confirmModal={confirmModal}
        closeModal={closeDeleteModal}
        loading={deleteTemplate.isLoading}
      />
      <Modal
        open={tempPreview}
        onCancel={tempPreviewClose}
        closable={false}
        width={937}
        styles={{
          content: {
            padding: 0,
            background: "#F4F3F6"
          }
        }}
        onClose={tempPreviewClose}
        footer={null}
      >
        <Flex
          justify="space-between"
          align="center"
          className="h-[64px] bg-white px-[24px] rounded-t-lg"
        >
          <span className="text-[16px] font-[#2A2A2A] font-bold">
            {tempPreviewInfo.name}
          </span>
          <div>
            <Button
              type="primary"
              style={{
                borderRadius: "4px",
                background: `linear-gradient(99.9deg, #2B69FF -4.18%, #8F91FF 106.52%)`,
                color: "#fff",
                border: "none",
                marginRight: "30px",
                padding: "5px 10px",
                fontSize: "14px"
              }}
              onClick={() => handleAction("toWrite", tempPreviewInfo.itemData)}
            >
              使用模板
            </Button>
            <CloseOutlined
              onClick={tempPreviewClose}
              style={{ fontSize: "14px" }}
            />
          </div>
        </Flex>
        <div className="py-5 px-6">
          <TempPreview
            htmlTemp={tempPreviewInfo.htmlTemp}
            cssTemp={tempPreviewInfo.cssTemp}
          />
        </div>
      </Modal>
      <div className="flex justify-center mt-16">
        {/* <AiBoy className="w-[42px] h-[68px] mr-[16px]" /> */}
        <div>
          <div className="font-bold text-[28px] text-text-color1 text-center">
            {/* Hi，欢迎使用中电金信大模型文档写作平台～ */}
            Hi，欢迎使用大模型文档写作平台～
          </div>
          <div className="text-[14px] text-[#888888] mt-[10px] text-center">
            在这里你可以轻松完成各类文档的撰写、润色、审核，不再为写作发愁
          </div>
        </div>
      </div>
      <div className="flex justify-center mt-[25px] mb-2">
        {/* 20251215隐藏上传 */}
        {/* <Button type="primary" ghost className="mr-[12px] rounded-3xl">
          <input
            type="file"
            accept=".docx,.doc"
            className="w-full h-full absolute top-0 left-0 opacity-0"
            onChange={handleFileChange}
            // 通过key处理两次选择一样的文件，不触发onChange的问题
            key={fileRefresh}
          />
          上传文档
        </Button> */}
        <Button
          type="primary"
          className="rounded-3xl"
          style={{
            background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
            color: "#fff",
            border: "none"
          }}
          onClick={() => handleAction("article_create", "normal")}
        >
          开始写作
        </Button>
      </div>
      {tempClassList.map((item: any) => {
        return item?.list?.length > 0 ? (
          <div
            key={item.class}
            className="w-[1086px] border-[1px] border-solid border-white bg-[rgba(255,255,255,.3)] rounded-[8px] mt-8 px-[16px] py-[16px]"
          >
            <div className="flex items-center justify-between pb-[16px]">
              <div className="text-text-color1 text-[16px] font-bold cursor-default">
                {item.class}
              </div>
            </div>
            <div className="flex flex-wrap grid-cols-6 gap-4">
              {item.list.map((n: any, index: number) => {
                return (
                  <Card key={uniqueId()} item={n} handleEvent={handleAction} />
                );
              })}
            </div>
          </div>
        ) : null;
      })}
      <div className="absolute right-9 top-9">
        <Dropdown
          menu={{ items: docList }}
          onOpenChange={onDocListOpenChange}
          dropdownRender={(menu) => (
            <div className="bg-[#FFFFFF] w-[280px] rounded-lg px-1 pt-5 pb-3">
              <div className="text-base text-[#2a2a2a] mb-3 px-5">
                <b>最近文档</b>
              </div>
              <div>
                {React.cloneElement(menu as React.ReactElement, {
                  style: {
                    boxShadow: "none"
                  }
                })}
              </div>
            </div>
          )}
        >
          <a onClick={(e) => e.preventDefault()}>
            {listDropDownShow ? (
              <ListClickSvg className="w-9 h-9 -mt-5" />
            ) : (
              <ListSvg className="w-9 h-9 -mt-5" />
            )}
          </a>
        </Dropdown>
      </div>
    </div>
  );
}

export default DocWriting;
