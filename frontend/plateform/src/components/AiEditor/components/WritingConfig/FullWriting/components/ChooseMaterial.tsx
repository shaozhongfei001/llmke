import {
  Button,
  Checkbox,
  ConfigProvider,
  Flex,
  Input,
  Modal,
  Tabs,
  TabsProps,
  Tag,
  Upload
} from "antd";
import { SearchOutlined } from "@ant-design/icons";
import {
  ChangeEventHandler,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";
import doc from "@/assets/writing/doc.png";
import { useHServices } from "../common/useRServices";
import { FILEIMG } from "../../../FileViewModal";
import { sceneTagMap, styleTagMap } from "../common/constans";
import "../common/style.less";
import "./style.less";

export enum UPLOAD_TYPE {
  TYPE_CHANGE = "type_change",
  CONFIRM = "confirm"
}

interface UploadFileTypeProps {
  open: boolean;
  title?: string;
  options?: Option[];
  handleChooseEvent?: (type: UPLOAD_TYPE, arg: any) => void;
  close: () => void;
  defaultData: any[];
}

export interface Option {
  value: string;
  label: string;
  children?: Option[];
}

const OPTIONS: Option[] = [
  {
    value: "zhejiang",
    label: "Zhejiang",
    children: [
      {
        value: "hangzhou",
        label: "Hanzhou",
        children: [
          {
            value: "xihu",
            label: "West Lake"
          }
        ]
      }
    ]
  },
  {
    value: "jiangsu",
    label: "Jiangsu",
    children: [
      {
        value: "nanjing",
        label: "Nanjing",
        children: [
          {
            value: "zhonghuamen",
            label: "Zhong Hua Men"
          }
        ]
      }
    ]
  }
];

export enum UPLOAD_EVENTS {
  MODAL_CLOSE = "upload_event:model_close",
  FILE_REMOVE = "upload_event:remove",
  FILE_UPLOADED = "upload_event:uploaded",
  MODAL_ONLY_CLOSE = "upload_event:model_only_close"
}

export enum FILE_STATUS {
  FINISHED = "finished"
}

const items: TabsProps["items"] = [
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

const ChooseMaterial = (props: UploadFileTypeProps) => {
  const {
    open,
    title = "选择素材",
    options = OPTIONS,
    defaultData,
    close,
    handleChooseEvent
  } = props;

  const [listPostData, setListPostData] = useState<{
    pageNo: number;
    pageSize: number;
    search: undefined | string;
    bizType: string;
    scene: string;
    articleStyle: string;
    totalCount: number;
  }>({
    pageNo: 1,
    pageSize: 9999,
    search: undefined,
    bizType: "commonLib",
    scene: "",
    articleStyle: "",
    totalCount: 0
  });
  const [taskIds, setTaskIds] = useState<string>("");
  const [listData, setListData] = useState<any[]>([]);
  const [checkedValue, setCheckedValue]: any = useState([]);
  const [activeTabKey, setActiveTabKey] = useState("commonLib");
  const [selectedSenceTags, setSelectedSenceTags] = useState<string[]>([]);
  const [selectedStyleTags, setSelectedStyleTags] = useState<string[]>([]);
  const allLists: any = useRef({});
  const { getMaterialList }: any = useHServices({
    taskIds,
    ...listPostData
  });
  const [fuzzyNameOrId, setFuzzyNameOrId] = useState("");
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [allCheckedFile, setAllCheckedFile]: any = useState({});
  const [allChecked, setAllChecked]: any = useState({
    commonLib: false,
    demoLib: false,
    lawLib: false
  });

  const closeModal = () => {
    close();
  };

  const modalStyles = {
    content: { padding: "20px", borderRadius: "8px" }
  };

  const handleConfirm = () => {
    const lists = allLists.current;

    const files = items.reduce((pre: any, cur) => {
      const curList = lists[cur.key] || [];
      if (activeTabKey === cur.key) {
        return pre.concat(
          curList.filter((item: any) => {
            return checkedValue.includes(item.id);
          })
        );
      } else {
        const curChecked = allCheckedFile[cur.key] || [];
        return pre.concat(
          curList.filter((item: any) => {
            return curChecked.includes(item.id);
          })
        );
      }
    }, []);
    handleChooseEvent && handleChooseEvent(UPLOAD_TYPE.CONFIRM, files);
  };
  const docKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      setListPostData({
        ...listPostData,
        pageNo: 1,
        search: fuzzyNameOrId
      });
    }
  };
  const fuzzyNameOrIdOnChange: ChangeEventHandler<HTMLInputElement> = (e) => {
    const inputElement = e.target as HTMLInputElement;
    setFuzzyNameOrId(inputElement.value.trim());
  };

  const handleEvent = async (action: string, data?: any) => {
    switch (action) {
      case "tabChange":
        setActiveTabKey(data);
        setSelectedSenceTags([]);
        setSelectedStyleTags([]);
        setAllCheckedFile((pre: any) => {
          return { ...pre, [activeTabKey]: checkedValue };
        });
        setCheckedValue(allCheckedFile[data] || []);
        break;
      default:
        return;
    }
  };

  const handleStyleTagChange = (tag: string, checked: boolean) => {
    const nextSelectedTags = checked
      ? [...selectedStyleTags, tag]
      : selectedStyleTags.filter((t) => t !== tag);
    setSelectedStyleTags(nextSelectedTags);
  };

  const handleSenceTagChange = (tag: string, checked: boolean) => {
    const nextSelectedTags = checked
      ? [...selectedSenceTags, tag]
      : selectedSenceTags.filter((t) => t !== tag);
    setSelectedSenceTags(nextSelectedTags);
  };

  useEffect(() => {
    if (open) {
      if (!getMaterialList?.data) return;

      const { details: list, totalCount, pageNo } = getMaterialList.data.data;
      const displayList = (list || []).filter((li) => li.state == 3);

      allLists.current[activeTabKey] = displayList || [];
      setListData(displayList || []);
      setListPostData({
        ...listPostData,
        totalCount
      });
    }
  }, [getMaterialList.data, open]);

  useEffect(() => {
    const sence: string[] = [];
    const articleStyle: string[] = [];
    sceneTagMap.forEach((se) => {
      if (selectedSenceTags.includes("全部")) return;
      if (selectedSenceTags.includes(se.label)) {
        sence.push(se.key);
      }
    });
    styleTagMap.forEach((se) => {
      if (selectedStyleTags.includes("全部")) return;
      if (selectedStyleTags.includes(se.label)) {
        articleStyle.push(se.key);
      }
    });
    setListPostData({
      ...listPostData,
      bizType: activeTabKey,
      pageNo: 1,
      scene: sence.join(","),
      articleStyle: articleStyle.join(",")
    });
  }, [activeTabKey, selectedSenceTags, selectedStyleTags]);

  const choosedCount = useMemo(() => {
    return items.reduce((pre, cur) => {
      if (activeTabKey === cur.key) {
        return pre + checkedValue.length;
      } else {
        return pre + (allCheckedFile[cur.key]?.length || 0);
      }
    }, 0);
  }, [allCheckedFile, checkedValue]);

  const onAllChange = (e) => {
    setAllChecked({
      ...allChecked,
      [activeTabKey]: e.target.checked
    });
    if (e.target.checked) {
      const _checkedValue = Array.from(
        new Set([...checkedValue, ...listData.map((li) => li.id)])
      );
      setCheckedValue([..._checkedValue]);
    } else {
      const _checkedValue = checkedValue.filter(
        (id: number) => !listData.some((i: any) => i.id === id)
      );
      setCheckedValue([..._checkedValue]);
      setAllCheckedFile((pre: any) => {
        return { ...pre, [activeTabKey]: [] };
      });
    }
  };

  const checkedValueOnChange = (list: Array<number>) => {
    const noCheckIds = (listData || [])
      .filter((i: any) => !list.includes(i.id))
      .map((i: any) => i.id);

    const _checkedValue = Array.from(
      new Set([...checkedValue, ...list])
    ).filter((id: number) => !noCheckIds.includes(id));
    setCheckedValue([..._checkedValue]);
  };

  useEffect(() => {
    if (!open) {
      setActiveTabKey("commonLib");
      setCheckedValue([]);
      setSelectedSenceTags([]);
      setSelectedStyleTags([]);
      setAllCheckedFile({});
      setAllChecked({});
      setListPostData({
        pageNo: 1,
        pageSize: 9999,
        search: undefined,
        bizType: "commonLib",
        scene: "",
        articleStyle: "",
        totalCount: 0
      });
    } else {
      getMaterialList.refetch();
    }
  }, [defaultData, open]);

  return (
    <ConfigProvider
      modal={{
        styles: modalStyles
      }}
    >
      <Modal
        open={open}
        title={<span className="text-[16px] font-normal">{title}</span>}
        width={973}
        destroyOnClose={true}
        cancelText={"取消"}
        okText={"确定"}
        footer={null}
        onCancel={closeModal}
        closable={false}
      >
        <Input
          value={fuzzyNameOrId}
          placeholder="输入名称搜索"
          style={{ width: "100%" }}
          className="bg-[#f5f5f5]"
          suffix={
            <div
              className="cursor-pointer"
              onClick={() => {
                setListPostData({
                  ...listPostData,
                  pageNo: 1,
                  search: fuzzyNameOrId
                });
              }}
            >
              <SearchOutlined style={{ color: "#999", fontSize: 16 }} />
            </div>
          }
          onChange={fuzzyNameOrIdOnChange}
          onKeyDown={docKeyDown}
        />
        <Tabs
          size="small"
          defaultActiveKey="1"
          activeKey={activeTabKey}
          items={items}
          className="chooseMaterail chooseMaterailTab"
          onChange={(key: string) => handleEvent("tabChange", key)}
        />
        <div className="h-[433px] flex flex-col chooseMaterail">
          <div className="material mt-[16px]">
            {activeTabKey == "demoLib" && (
              <Flex>
                <div className="font-bold w-[50px] h-[32px] leading-[32px]">
                  文体
                </div>
                <div>
                  {styleTagMap.map<React.ReactNode>((tag) => (
                    <Tag.CheckableTag
                      key={tag.key}
                      checked={selectedStyleTags.includes(tag.label)}
                      onChange={(checked) =>
                        handleStyleTagChange(tag.label, checked)
                      }
                      className="bg-[#F5F6FA] hover:text-[#055AFF] hover:bg-[#E2E9FF] text-[14px] mb-[12px] h-[32px] leading-[32px]"
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
                  场景
                </div>
                <div>
                  {sceneTagMap.map<React.ReactNode>((tag) => (
                    <Tag.CheckableTag
                      key={tag.key}
                      checked={selectedSenceTags.includes(tag.label)}
                      onChange={(checked) =>
                        handleSenceTagChange(tag.label, checked)
                      }
                      className="bg-[#F5F6FA] hover:text-[#055AFF] hover:bg-[#E2E9FF] text-[14px] mb-[12px] h-[32px] leading-[32px]"
                    >
                      {tag.label}
                    </Tag.CheckableTag>
                  ))}
                </div>
              </Flex>
            )}
          </div>
          <div className="overflow-auto flex-1">
            <Checkbox.Group
              style={{ width: "100%" }}
              onChange={checkedValueOnChange}
              value={checkedValue}
            >
              {listData.map((item) => {
                return (
                  <div
                    className="w-full h-[53px] flex items-center px-[16px]"
                    style={{ borderBottom: "1px solid #EEEEEE" }}
                    key={item.id}
                  >
                    <Checkbox value={item.id}>
                      <div className="flex items-center mt-[5px]">
                        <img
                          src={FILEIMG[item.fileSuffix] || doc}
                          alt="ellipse"
                          width={20}
                          height={20}
                          className="ml-[16px] mr-[24px]"
                        />
                        <div>{item.fileName}</div>
                      </div>
                    </Checkbox>
                  </div>
                );
              })}
            </Checkbox.Group>
          </div>
          {/* <div className="w-full flex justify-end mt-[20px]">
            <Pagination
              simple
              defaultCurrent={1}
              total={listPostData.totalCount || 0}
              size="small"
              current={listPostData.pageNo}
              onChange={() => {}}
              showSizeChanger={false}
            />
          </div> */}
        </div>
        <div className="flex justify-between">
          <div className="flex items-center mt-[24px] pl-[0px]">
            <Checkbox onChange={onAllChange} checked={allChecked[activeTabKey]}>
              全选
            </Checkbox>
            <div className=" text-text-color2 ">
              已选择<span className="text-[#055AFF]">{choosedCount}</span>个文件
            </div>
          </div>

          <div
            className="flex justify-end pt-[24px]"
            // style={{ borderTop: "1px solid #eee" }}
          >
            <Button
              style={{
                border: "1px solid #ebebeb",
                color: "#555",
                marginRight: "16px",
                borderRadius: "4px"
              }}
              onClick={closeModal}
            >
              取消
            </Button>
            <Button
              type="primary"
              style={{
                background: `linear-gradient(to bottom right, #2B69FF 0%, #8F91FF 80%)`,
                opacity: choosedCount <= 0 ? "50%" : "100%",
                color: "#fff",
                border: "none",
                borderRadius: "4px"
              }}
              onClick={handleConfirm}
              disabled={choosedCount <= 0}
              loading={confirmLoading}
            >
              确定
            </Button>
          </div>
        </div>
      </Modal>
    </ConfigProvider>
  );
};

export default ChooseMaterial;
