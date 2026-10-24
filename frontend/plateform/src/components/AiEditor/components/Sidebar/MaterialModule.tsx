import {
  Select,
  Input,
  Flex,
  Tag,
  Tabs,
  List,
  ConfigProvider,
  Modal,
  message,
  Button
} from "antd";
import { useEffect, useState } from "react";
import { api_getArticleMaterialList } from "@/components/AiEditor/core/services/servers";
import { useStateStore } from "@/components/AiEditor/core/states/useStateStore";
import FileView from "./components/FileView";
import dayjs from "dayjs";
import newXls from "@/components/AiEditor/assets/img/newXls.png";
import newWord from "@/components/AiEditor/assets/img/newWord.png";
import newPdf from "@/components/AiEditor/assets/img/newPdf.png";
import newTxt from "@/components/AiEditor/assets/img/newTxt.png";
import newPpt from "@/components/AiEditor/assets/img/newPpt.png";
import newImg from "@/components/AiEditor/assets/img/newImg.png";
import newCsv from "@/components/AiEditor/assets/img/newCsv.png";
import outher from "@/components/AiEditor/assets/img/default.png";
import "./index.css";
import StyledTitle from "../common/StyledTitle";
import { ModueEnum } from "../../@types/sys";
import { SearchOutlined } from "@ant-design/icons";

const { Search } = Input;

const FILEIMG: any = {
  docx: newWord,
  doc: newWord,
  pdf: newPdf,
  xls: newXls,
  xlsx: newXls,
  ppt: newPpt,
  pptx: newPpt,
  pub: newPpt,
  jpg: newImg,
  png: newImg,
  txt: newTxt,
  csv: newCsv,
  default: outher
};

const items = [
  {
    key: "commonLib",
    label: "我的上传"
  },
  {
    key: "demoLib",
    label: "范文库"
  },
  {
    key: "lawLib",
    label: "法规库"
  }
];
const senceTagMap = [
  // {
  //   key: 'all',
  //   label: '全部',
  // },
  {
    value: "scene_bank",
    label: "银行"
  },
  {
    value: "scene_insurance",
    label: "保险"
  },
  {
    value: "scene_security",
    label: "证券"
  },
  {
    value: "scene_other",
    label: "其他"
  }
];
const styleTagMap = [
  // {
  //   value: 'all',
  //   label: '全部',
  // },
  {
    value: "style_notice",
    label: "通知公告"
  },
  {
    value: "style_report",
    label: "工作报告"
  },
  {
    value: "style_survey",
    label: "调研报告"
  },
  {
    value: "style_invitation",
    label: "邀请函"
  },
  {
    value: "style_understanding",
    label: "心得体会"
  },
  {
    value: "style_speech",
    label: "讲话稿"
  },
  {
    value: "style_other",
    label: "其他"
  }
];

const styleTags = [
  "通知公告",
  "工作报告",
  "调研报告",
  "邀请函",
  "心得体会",
  "讲话稿"
];
const senceTags = ["银行", "证券", "保险"];

const ResourceM = () => {
  const [activeTabKey, setActiveTabKey] = useState("commonLib");
  const [fuzzyNameOrId, setFuzzyNameOrId] = useState("");
  const [listData, setListData] = useState([]);
  const { serverInfo } = useStateStore();
  const [selected, setSelected] = useState<any[]>([]);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [curFileInfo, setCurFileInfo] = useState({
    file_source: "",
    fileName: "",
    fileSuffix: ""
  });
  const [selectOpen, setSelectOpen] = useState(false);
  const { setOpen, open, setProjectData } = useStateStore();
  const tabChange = (key: string) => {
    setFuzzyNameOrId("");
    setActiveTabKey(key);
    setSelectedSenceTags([]);
    setSelectedStyleTags([]);
    setSelected([]);
  };

  const [selectedSenceTags, setSelectedSenceTags] = useState<any[]>([]);
  const handleSenceTagChange = (tag: any, checked: boolean) => {
    const nextSelectedTags = checked
      ? [...selectedSenceTags, tag.value]
      : selectedSenceTags.filter((t) => t !== tag.value);
    setSelectedSenceTags(nextSelectedTags);
  };

  const [selectedStyleTags, setSelectedStyleTags] = useState<any[]>([]);
  const handleStyleTagChange = (tag: any, checked: boolean) => {
    const nextSelectedTags = checked
      ? [...selectedStyleTags, tag.value]
      : selectedStyleTags.filter((t) => t !== tag.value);
    setSelectedStyleTags(nextSelectedTags);
  };

  const onFinish = () => {
    const sence = senceTagMap.filter((s) => {
      if (selectedSenceTags.includes(s.value)) {
        return s;
      }
    });
    const style = styleTagMap.filter((s) => {
      if (selectedStyleTags.includes(s.value)) {
        return s;
      }
    });
    setSelected([...style, ...sence]);
    setSelectOpen(false);
  };

  const onSearch = (val: string) => {
    setFuzzyNameOrId(val);
  };

  const getMaterialList = async () => {
    let sence: string[] = [];
    let articleStyle: string[] = [];
    selected.forEach((se) => {
      const tag = se.value.split("_")[1];
      if (se.value.indexOf("style") > -1) {
        articleStyle.push(tag);
      }
      if (se.value.indexOf("scene") > -1) {
        sence.push(tag);
      }
    });
    const res = await api_getArticleMaterialList({
      data: {
        fileName: fuzzyNameOrId,
        bizType: activeTabKey,
        scene: sence.join(","),
        articleStyle: articleStyle.join(","),
        pageSize: 999,
        pageNo: 1
      },
      config: serverInfo
    });
    setListData(res.details);
  };

  useEffect(() => {
    getMaterialList();
  }, [activeTabKey, selected]);

  const showDoc = (data: any) => {
    if (data && data?.id) {
      const { fileName, fileUrl, htmlUrl, fileSuffix } = data;
      const isFrontRender =
        ["pdf", "txt", "html", "csv", "img"].indexOf(fileSuffix) > -1;
      if (!isFrontRender && (!htmlUrl || JSON.parse(htmlUrl)?.length <= 0)) {
        message.warning("请解析成功后查看");
        return;
      }
      setShowPreviewModal(true);
      let url = isFrontRender ? fileUrl : JSON.parse(htmlUrl);
      url = Array.isArray(url) ? url.map((u: any) => u.url) : url;
      url = Array.isArray(url) && url?.length == 1 ? url[0] : url;

      setCurFileInfo({
        file_source: url,
        fileName: fileName,
        fileSuffix: fileSuffix
      });
    } else {
      message.warning("该文档为空");
    }
  };

  const handleE = (type: string) => {
    switch (type) {
      case "close":
        setShowPreviewModal(false);
        break;
    }
  };

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
  const getTag = (item: any, activeKey: string) => {
    const articleStyle =
      styleTagMap
        .concat([
          {
            value: "style_all",
            label: "全部"
          }
        ])
        .find((s) => s.value.split("_")[1] == item.articleStyle)?.label || "";
    const sence =
      senceTagMap
        .concat([
          {
            value: "style_all",
            label: "全部"
          }
        ])
        .find((s) => s.value.split("_")[1] == item.scene)?.label || "";
    switch (activeKey) {
      case "demoLib":
        {
          if (item.articleStyle && item.scene) {
            return (
              <div className="h-[20px] mx-[4px] leading-[20px]">
                {articleStyle} · {sence}
              </div>
            );
          } else {
            return (
              <div className="h-[20px] mx-[4px] leading-[20px]">
                {articleStyle || sence}
              </div>
            );
          }
        }
        return;
      case "lawLib":
        return <div className="h-[20px] mx-[4px] leading-[20px]">{sence}</div>;
    }
  };
  const closeSidebar = () => {
    setOpen(false);
    setProjectData((p) => ({
      ...p,
      currentModule: ModueEnum.Writing
    }));
  };
  return (
    <div className="h-full relative overflow-hidden w-full material-box">
      <StyledTitle title="素材" close={closeSidebar} />
      <div className="px-5 py-0 my-0 w-full">
        <Tabs
          activeKey={activeTabKey}
          items={items}
          onChange={tabChange}
          className="my-0 py-0 h-[50px]"
        />
      </div>
      <div className="px-5 mt-4 border-color-cls">
        <Input
          value={fuzzyNameOrId}
          placeholder="搜索内容"
          className="mb-[10px] h-[32px]"
          suffix={
            <SearchOutlined
              style={{ color: "#999", fontSize: 16 }}
              onClick={getMaterialList}
            />
          }
          onChange={(e) => setFuzzyNameOrId(e.target.value)}
        />
        {activeTabKey !== "commonLib" && (
          <Select
            className="w-full"
            placeholder="选择类型"
            mode="multiple"
            showSearch={false}
            value={selected}
            open={selectOpen}
            labelInValue
            onDropdownVisibleChange={() => {
              setSelectOpen(true);
            }}
            onDeselect={(value) => {
              setSelectedSenceTags((pre) =>
                pre.filter((p) => p !== value.value)
              );
              setSelectedStyleTags((pre) =>
                pre.filter((p) => p !== value.value)
              );
              setSelected((pre) => pre.filter((p) => p.value !== value.value));
            }}
            dropdownRender={(menu) => (
              <div className="material p-[16px]">
                {activeTabKey == "demoLib" && (
                  <Flex>
                    <div className="font-bold w-[50px] h-[32px] leading-[32px]">
                      文体:
                    </div>
                    <div className="flex-1">
                      {styleTagMap.map<React.ReactNode>((tag) => (
                        <Tag.CheckableTag
                          key={tag.value}
                          checked={selectedStyleTags.includes(tag.value)}
                          onChange={(checked) =>
                            handleStyleTagChange(tag, checked)
                          }
                          style={{
                            background: selectedStyleTags.includes(tag.value)
                              ? "#E2E9FF"
                              : "#f5f6fa",
                            color: selectedStyleTags.includes(tag.value)
                              ? "#055aff"
                              : "#2a2a2a"
                          }}
                          className="text-[14px] mb-[12px] h-[32px] leading-[32px]"
                        >
                          {tag.label}
                        </Tag.CheckableTag>
                      ))}
                    </div>
                  </Flex>
                )}
                {(activeTabKey == "lawLib" || activeTabKey == "demoLib") && (
                  <Flex>
                    <div className="font-bold w-[50px] h-[32px] leading-[32px]">
                      场景:
                    </div>
                    <div className="flex-1">
                      {senceTagMap.map<React.ReactNode>((tag) => (
                        <Tag.CheckableTag
                          key={tag.value}
                          checked={selectedSenceTags.includes(tag.value)}
                          onChange={(checked) =>
                            handleSenceTagChange(tag, checked)
                          }
                          style={{
                            background: selectedSenceTags.includes(tag.value)
                              ? "#E2E9FF"
                              : "#f5f6fa",
                            color: selectedSenceTags.includes(tag.value)
                              ? "#055aff"
                              : "#2a2a2a"
                          }}
                          className="text-[14px] mb-[12px] h-[32px] leading-[32px]"
                        >
                          {tag.label}
                        </Tag.CheckableTag>
                      ))}
                    </div>
                  </Flex>
                )}

                <div className="w-full ml-[12px] flex flex-row justify-end align-center mt-[20px]">
                  <Button
                    type="primary"
                    onClick={() => {
                      if (selected.length > 0) {
                        setSelectOpen(false);
                      } else {
                        setSelectOpen(false);
                        setSelected([]);
                        setSelectedSenceTags([]);
                        setSelectedStyleTags([]);
                      }
                    }}
                    style={{
                      color: `#555555`,
                      backgroundColor: "#fff",
                      borderRadius: "4px",
                      border: "1px solid #dedede"
                    }}
                  >
                    取消
                  </Button>
                  <Button
                    ghost
                    onClick={onFinish}
                    style={{
                      background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                      color: "#fff",
                      border: "none",
                      borderRadius: "4px",
                      marginLeft: "10px"
                    }}
                  >
                    确认
                  </Button>
                </div>
              </div>
            )}
          />
        )}
      </div>
      <div
        id="scrollableDiv"
        className="bg-white h-[calc(100%-220px)] rounded-[8px] overflow-y-auto overflow-x-hidden pl-5 pr-4 pt-3"
      >
        <List
          dataSource={listData}
          bordered={false}
          split={false}
          rowKey={(item) => item.id}
          renderItem={(item: any) => (
            <List.Item
              onClick={() => showDoc(item)}
              style={{ padding: 0, marginBottom: "12px" }}
            >
              <div className="bg-white cursor-pointer w-full items-start px-[16px] py-[20px] h-[114px] rounded-[4px] border-[1px] border-solid border-[#EDEDED] hover:border-primary-color">
                <div className="text-[16px] font-bold line-clamp-2 text-ellipsis break-words h-[50px] text-[#2A2A2A] mb-3">
                  {item.fileName}
                </div>
                <div className="flex w-full text-[12px] line-clamp-1 text-ellipsis break-words items-center justify-between">
                  <div className="flex flex-row bg-[#E0EEFF]  rounded-[4px] items-center text-[#6B6E99]">
                    <div className="w-[20px] h-[20px] bg-[#FFFFFF] rounded flex justify-center items-center">
                      <img
                        src={FILEIMG[item.fileSuffix] || FILEIMG["default"]}
                        alt="ellipse"
                        width={12}
                      />
                    </div>
                    {getTag(item, activeTabKey)}
                  </div>
                  <div className="line-clamp-1 text-ellipsis break-words text-[#888]">
                    {item.gmtModified &&
                      dayjs(item.gmtModified).format("YYYY-MM-DD")}
                  </div>
                </div>
              </div>
            </List.Item>
          )}
        />
      </div>
      <ConfigProvider
        modal={{
          styles: modalStyles
        }}
      >
        <Modal
          destroyOnClose={true}
          open={showPreviewModal}
          onCancel={() => {
            setCurFileInfo({
              file_source: "",
              fileName: "",
              fileSuffix: ""
            });
            setShowPreviewModal(false);
          }}
          width={900}
          height={742}
          closable={false}
          maskClosable={false}
          footer={null}
        >
          <div className="h-[600px] overflow-y-auto">
            <FileView curFileInfo={curFileInfo} handleEvent={handleE} />
          </div>
        </Modal>
      </ConfigProvider>
    </div>
  );
};

export default ResourceM;
