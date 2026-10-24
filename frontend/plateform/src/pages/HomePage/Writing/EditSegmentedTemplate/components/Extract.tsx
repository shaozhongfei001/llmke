import { useCallback, useState, useMemo, useEffect, useRef } from "react";
import {
  Input,
  Button,
  Flex,
  Tree,
  Modal,
  Tabs,
  ConfigProvider,
  Select
} from "antd";
import FileViewCec from "@root/src/components/FileViewCec";
import IconFile from "@/assets/knowledgebase/icon-file.svg";
import plusBlue from "@root/src/assets/img/plusBlue.png";
import doc from "@/assets/writing/doc.png";
import UploadFileType from "./UploadOne";
import extractFail from "@/assets/img/extractFail.png";
import "../index.less";
import { Label } from "@radix-ui/react-dropdown-menu";
import axios$ from "@root/src/apis";
import { queryEditor } from "@udecode/plate-common";
import Paragraph from "antd/es/skeleton/Paragraph";
const modalStyles = {
  header: {
    padding: "20px 24px",
    borderBottom: "1px solid #F0F0F0",
    margin: 0
  },
  body: { padding: 0 },
  mask: {},
  footer: { padding: 0, margin: 0 },
  content: { padding: 0 }
};

const titleMap = {
  0: "一",
  1: "二",
  2: "三",
  3: "四",
  4: "五",
  5: "六",
  6: "七",
  7: "八",
  8: "九",
  9: "十"
};

const options = [
  { value: "一、", label: "一、标题名称" },
  { value: "（一）", label: "（一）标题名称" },
  { value: "1.", label: "1. 标题名称" },
  { value: "（1）", label: "（1）标题名称" }
];

const Extract = ({
  id,
  applyOutlines,
  setExpandedRowKeys,
  allOutlineIds
}: any) => {
  const [allExpand, setAllExpand] = useState<boolean>(false);
  const [uploadModalOpen, setUploadModalOpen] = useState<boolean>(false);
  const [showPreviewModal, setShowPreviewModal] = useState<boolean>(false);
  const [activeKey, setActiveKey] = useState("1");
  const [titleList, setTitleList] = useState([
    {
      label: "一级标题",
      value: ""
    },
    {
      label: "二级标题",
      value: ""
    },
    {
      label: "三级标题",
      value: ""
    }
  ]);
  const [extractRes, setExtractRes] = useState(); //抽取结果
  const [file, setFile] = useState();

  const uploadSeq = async () => {
    const formData = new FormData();
    formData.append("file", file.originFile);
    const titleExamples: string[] = [];
    titleList.forEach((t) => {
      if (t.value?.length > 0) return titleExamples.push(t.value);
    });
    if (titleExamples?.length > 0) {
      formData.append("titleExamples", titleExamples);
    }

    try {
      const res = await axios$.post(
        `/cecProxy/dw/articleType/genOutlinesByDocx`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data"
          }
        }
      );
      if (res) {
        setExtractRes(res.data);
        setActiveKey("1");
      }
    } catch (error) {
      console.log("====================================");
      console.log("error", error);
      console.log("====================================");
    }
  };

  const treeData = useMemo(() => {
    const traverse = (data: any[]) => {
      return (data || []).filter((item: any) => {
        if (item.subParagraphs) {
          item.subParagraphs = traverse(item.subParagraphs);
        }
        item.title = item.title?.trim();
        return item.title !== "";
      });
    };

    return traverse(extractRes?.paragraphs);
  }, [extractRes?.paragraphs]);

  const renderRes = useCallback(() => {
    if (
      extractRes &&
      extractRes?.paragraphs &&
      extractRes?.paragraphs?.length > 0
    ) {
      return (
        <Tree
          fieldNames={{
            title: "title",
            key: "title",
            children: "subParagraphs"
          }}
          titleRender={(node) => {
            if (node?.title?.length > 50) {
              return (
                <span className="w-full">
                  {node?.title.substring(0, 49) + "..."}
                </span>
              );
            } else {
              return <span>{node?.title}</span>;
            }
          }}
          treeData={treeData}
        />
      );
    } else {
      return (
        <div className="w-full h-[500px] flex flex-col items-center justify-center">
          <img src={extractFail} className="w-[130px] h-[120px]" />
          <div className="mt-[16px]">
            抽取结果失败，建议先
            <span
              className="text-[#055AFF] cursor-pointer"
              onClick={() => {
                setActiveKey("2");
              }}
            >
              配置规则
            </span>
          </div>
        </div>
      );
    }
  }, [extractRes]);

  const closeModal = () => {
    setTitleList([
      {
        label: "一级标题",
        value: ""
      },
      {
        label: "二级标题",
        value: ""
      },
      {
        label: "三级标题",
        value: ""
      }
    ]);
    setShowPreviewModal(false);
  };

  const renderFooterBtn = () => {
    switch (activeKey) {
      case "1":
        return (
          <>
            <Button
              className="border-[#EEEEEE] text-[#555555]"
              onClick={() => {
                uploadSeq();
              }}
            >
              重新抽取
            </Button>
            {extractRes &&
            extractRes?.paragraphs &&
            extractRes?.paragraphs?.length > 0 ? (
              <Button
                style={{
                  background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                  color: "#fff",
                  border: "none"
                }}
                onClick={async () => {
                  const res = await applyOutlines({
                    paragraphs: treeData
                  });
                  if (res) closeModal();
                }}
              >
                应用
              </Button>
            ) : (
              <Button
                style={{
                  background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                  color: "#fff",
                  border: "none"
                }}
                onClick={() => {
                  setActiveKey("2");
                }}
              >
                配置规则
              </Button>
            )}
          </>
        );

      case "2":
        return (
          <>
            <Button
              className="border-[#EEEEEE] text-[#555555]"
              onClick={() => {
                setShowPreviewModal(false);
              }}
            >
              取消
            </Button>
            <Button
              style={{
                background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                color: "#fff",
                border: "none"
              }}
              onClick={() => {
                uploadSeq();
              }}
            >
              抽取
            </Button>
          </>
        );
    }
  };

  const renderRule = () => {
    return (
      <>
        <div className="w-full flex flex-row justify-between items-center mb-[10px]">
          <span className="text-[14px] text-[#2A2A2A] font-bold ">
            标题样式配置
          </span>
          <Button
            size="small"
            className="text-text-color2 border-[#EEEEEE] w-[94px] text-[12px] flex-row items-center"
            icon={<img src={plusBlue} className="w-[12px] h-[12px] mt-[4px]" />}
            onClick={() => {
              setTitleList((pre) => [
                ...pre,
                {
                  label: `${titleMap[pre.length]}级标题`,
                  value: ""
                }
              ]);
            }}
          >
            添加标题
          </Button>
        </div>
        {titleList.map((title, idx) => {
          return (
            <div className="mb-[10px]" key={`title-${idx}`}>
              <Label>{title.label}</Label>
              <Select
                style={{ width: "100%", height: 32 }}
                options={options}
                onSelect={(val) => {
                  setTitleList((pre) => {
                    return pre.map((p) => {
                      if (p.label == title.label) {
                        p.value = val;
                      }
                      return p;
                    });
                  });
                }}
                value={title.value}
              />
            </div>
          );
        })}
      </>
    );
  };

  const renderPreview = () => {
    if (file && file?.fileUpload) {
      const parser = new DOMParser();
      const doc = parser.parseFromString(file?.fileUpload, "text/html");
      return doc.body.innerHTML;
    }
    return "";
  };

  return (
    <>
      <div className=" template-title w-full flex flex-row justify-between items-center mb-[10px]">
        <div>
          <span className="text-[14px] text-[#2A2A2A] font-bold ">大纲</span>
          <div
            className="one-click-expanded"
            onClick={() => {
              if (allExpand) {
                setExpandedRowKeys([]);
              } else {
                setExpandedRowKeys(allOutlineIds);
              }
              setAllExpand(!allExpand);
            }}
          >
            {allExpand ? "一键收起" : "一键展开"}
          </div>
        </div>

        <Button
          className="text-[#055AFF]  w-[108px] h-[24px]  text-center leading-[24px] border-[#EEEEEE]"
          onClick={() => setUploadModalOpen(true)}
          disabled={!!file}
        >
          上传模板文档
        </Button>
      </div>
      {file && (
        <div className="w-full flex flex-row justify-between items-center mb-[10px]">
          <div className="flex items-center">
            <img
              src={IconFile}
              style={{
                position: "relative",
                marginRight: "8px",
                top: "1px",
                marginLeft: "8px"
              }}
            />
            <div
              style={{
                fontSize: "12px",
                color: "#555",
                width: "330px"
              }}
              className="text-ellipsis break-words line-clamp-1"
            >
              {file?.originFile?.name}
            </div>
          </div>
          <span
            className="text-[#055AFF] font-[12px]"
            onClick={() => setFile(undefined)}
          >
            删除
          </span>
        </div>
      )}

      <UploadFileType
        open={uploadModalOpen}
        close={() => setUploadModalOpen(false)}
        uploadEvents={(file) => {
          console.log("-------file", file);
          if (file) {
            setUploadModalOpen(false);
            setFile(file);
            setShowPreviewModal(true);
            setExtractRes(file.extractRes);
          }
        }}
      />
      <ConfigProvider
        modal={{
          styles: modalStyles
        }}
      >
        <Modal
          title={
            <div className=" flex flex-row items-center ">
              <img
                src={doc}
                alt="ellipse"
                className="w-[16px] h-[16px]  bg-[#FFFFFF]  mr-[10px]"
              />
              <span>{file?.originFile?.name || "文件名"}</span>
            </div>
          }
          destroyOnClose={true}
          open={showPreviewModal}
          onCancel={() => {
            closeModal();
          }}
          width={1150}
          height={742}
          maskClosable={false}
          footer={
            <Flex
              className="h-[68px] pr-6"
              align="center"
              justify="flex-end"
              gap={16}
            >
              {renderFooterBtn()}
            </Flex>
          }
        >
          <div className="h-[600px] overflow-y-auto flex flex-row justify-between">
            <div
              className="w-[790px] overflow-x-auto"
              dangerouslySetInnerHTML={{ __html: renderPreview() }}
            ></div>
            <Tabs
              className="w-[350px] overflow-y-auto"
              items={[
                {
                  key: "1",
                  label: "抽取结果",
                  children: <div>{renderRes()}</div>
                },
                {
                  key: "2",
                  label: "配置规则",
                  children: <>{renderRule()}</>
                }
              ]}
              defaultActiveKey="1"
              activeKey={activeKey}
              onChange={(key) => {
                setActiveKey(key);
              }}
              style={{ padding: "0 16px 16px 16px" }}
            ></Tabs>
          </div>
        </Modal>
      </ConfigProvider>
    </>
  );
};

export default Extract;
