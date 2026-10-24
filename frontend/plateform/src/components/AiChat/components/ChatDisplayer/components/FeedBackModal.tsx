import { Button, ConfigProvider, Form, Modal, Input, Tree, Tag } from "antd";
import "./style.less";
import { Key, useEffect, useMemo, useRef, useState } from "react";
import downArrow from "../../../assets/img/downArrow.png";
import { RightOutlined } from "@ant-design/icons";
import { api_feed_back } from "../../../core/services/servers";
import { useStateStore } from "../../../core/useStateStore";
const { TextArea } = Input;
const { useForm } = Form;
const pKey: any = {
  回答不佳: "ansPoor",
  格式问题: "formatError",
  理解问题有误: "harmfulInfo",
  其他: "othres"
};
const FeedBackModal = ({
  open,
  setOpen,
  feedBackList,
  feedParam,
  setCurrentChat
}: any) => {
  const { serverInfo } = useStateStore();

  const modalStyles = {
    header: {
      padding: "20px 24px",
      borderBottom: "1px solid #F0F0F0",
      margin: 0
    },
    body: { padding: "16px 24px 20px 24px", borderBottom: "1px solid #F0F0F0" },
    mask: {},
    footer: { padding: "16px 24px", margin: 0 },
    content: { padding: 0, borderRadius: "4px", width: "563px" }
  };

  const [form] = useForm();
  const [treeSelectResult, setTreeSelectResult] = useState<null | any>({});

  const handleOk = async () => {
    try {
      const data = await form.validateFields();
      setOpen(false);
      const param = {
        ...data
      };
      Object.entries(treeSelectResult || {}).forEach((item) => {
        const [key, value] = item;
        if (value) {
          param[pKey[key]] = value;
        }
      });
      console.log("handleOk", param);
      api_feed_back({
        data: { ...feedParam, ...param },
        config: {
          url: serverInfo.baseURL,
          token: serverInfo.token,
          enableMock: serverInfo.mockMode
        }
      }).then((res) => {
        if (res) {
          setCurrentChat((pre: any) => {
            const newPre = pre.map((item: any) => {
              if (item.id === feedParam.queryId) {
                return {
                  ...item,
                  answer: { ...item.answer, feedbackResult: feedParam.restult }
                };
              }
              return item;
            });
            newPre.type = "feed";
            return newPre;
          });
        }
      });
    } catch (e) {
      console.log(e);
      return;
    }
  };

  useEffect(() => {
    if (!open) {
      form.resetFields();
      setTreeSelectResult(null);
    }
  }, [open]);

  return (
    <ConfigProvider
      modal={{
        styles: modalStyles
      }}
    >
      <Modal
        open={open}
        onCancel={() => setOpen(false)}
        title={
          <div className="text-[16px] text-[#2A2A2A] font-bold leading-[1]">
            感谢您的反馈！这将帮助我们不断优化与提升。
          </div>
        }
        footer={
          <div>
            <Button
              className="mr-[16px] w-[76px]"
              onClick={() => {
                setOpen(false);
              }}
            >
              取消
            </Button>
            <Button
              type="primary"
              className="w-[76px] border-none"
              onClick={handleOk}
            >
              确认
            </Button>
          </div>
        }
      >
        <SelectTreeCom
          feedBackList={feedBackList}
          treeSelectResult={treeSelectResult}
          setTreeSelectResult={setTreeSelectResult}
        />
        <Form form={form} layout="vertical">
          <Form.Item name="supplementExplain" label="补充描述">
            <TextArea />
          </Form.Item>{" "}
          <Form.Item name="idealAnswer" label="您觉得更好的回答是什么？">
            <TextArea />
          </Form.Item>
          <Form.Item name="userPhone" label="联系电话">
            <Input />
          </Form.Item>
          <Form.Item name="deptName" label="部门">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </ConfigProvider>
  );
};
export default FeedBackModal;

const SelectTreeCom = ({
  feedBackList,
  treeSelectResult,
  setTreeSelectResult
}: any) => {
  const [openSelect, setOpenSelect] = useState(false);
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);
  const [checkedKeys, setCheckedKeys] = useState<
    Key[] | { checked: Key[]; halfChecked: Key[] }
  >([]);
  const [selectedValue, setSelectedValue] = useState<
    Key[] | { checked: Key[]; halfChecked: Key[] }
  >([]);
  const [selectedParent, setSelectedParent] = useState<null | {
    que_name?: string;
    items?: string[];
  }>(null);
  const curTree = useMemo(() => {
    setCheckedKeys([]);
    return selectedParent?.items
      ? [
          {
            title: "全选",
            key: "全选",
            children: selectedParent.items.map((item) => {
              return {
                title: item,
                key: item
              };
            })
          }
        ]
      : [];
  }, [selectedParent]);

  const handleClose = (removedTag: any) => {
    setSelectedValue((pre: any) => {
      if (Array.isArray(pre) && Array.isArray(checkedKeys)) {
        const p = Object.entries(treeSelectResult).reduce(
          (pre: any, current: any) => {
            const [key, value] = current;
            const tags = value ? value.split(";") : [];
            const newTags = tags.filter((tag: any) => tag !== removedTag);
            setTreeSelectResult((pre: any) => {
              return {
                ...(pre || {}),
                [key]: newTags.join(";")
              };
            });
            return [...pre, ...newTags];
          },
          []
        );
        return p;
      }
      return pre;
    });
  };

  useEffect(() => {
    setExpandedKeys(["全选"]);
    if (!treeSelectResult || !selectedParent?.que_name) return;
    const res = treeSelectResult[selectedParent.que_name] || "";
    const curSelectedValue = res ? res.split(";") : [];
    setCheckedKeys(curSelectedValue);
  }, [curTree, openSelect]);

  useEffect(() => {
    if (treeSelectResult === null) {
      setSelectedValue([]);
      setSelectedParent(null);
      setCheckedKeys([]);
    }
  }, [treeSelectResult]);

  useEffect(() => {
    console.log("treeSelectResult", treeSelectResult);
    console.log("selectedValue", selectedValue);
    console.log("feedBackList", feedBackList);
    console.log("pKey", pKey);
    console.log("selectedParent", selectedParent);
  }, [treeSelectResult, selectedValue]);
  return (
    <div className="relative mb-[24px] z-20">
      <div className="absolute w-full z-10">
        <div
          className="h-[32px] box-border flex items-center justify-between border-[1px] border-solid border-[#D9D9D9] rounded-[4px] cursor-pointer"
          onClick={() => setOpenSelect(!openSelect)}
        >
          <div className="ml-[16px]">问题类型</div>
          <img src={downArrow} width={24} height={24} className="mr-[16px]" />
        </div>
        <div
          style={{ display: openSelect ? "" : "none" }}
          className="h-[288px] rounded-[4px] shadow-md mt-[4px] bg-white"
        >
          <div
            className="h-[248px] flex"
            style={{ borderBottom: "1px solid #F0F0F0" }}
          >
            <div
              className="w-[203px] px-[8px] py-[8px]"
              style={{ borderRight: "1px solid #F0F0F0" }}
            >
              {feedBackList.map((item: any, index: number) => {
                return (
                  <div
                    key={index}
                    className="rounded-[4px] h-[32px] cursor-pointer flex items-center"
                    style={{
                      backgroundColor:
                        selectedParent?.que_name === item.que_name
                          ? "#E6F4FF"
                          : ""
                    }}
                  >
                    <div
                      className="h-full w-full leading-[32px]"
                      onClick={() => {
                        setSelectedParent(item);
                      }}
                    >
                      <div className="ml-[8px] text-[14px] text-[#2A2A2A]">
                        {item.que_name}(
                        {treeSelectResult && treeSelectResult[item.que_name]
                          ? treeSelectResult[item.que_name].split(";").length
                          : 0}
                        /{item?.items?.length})
                      </div>
                    </div>
                    <RightOutlined className="mr-[8px] text-[12px] text-[rgba(0,0,0,0.45)]" />
                  </div>
                );
              })}
            </div>
            <div className="selfTree h-full flex-1 mt-[8px] ml-[16px]">
              <Tree
                checkable
                defaultSelectedKeys={["0-1"]}
                treeData={curTree}
                blockNode
                checkedKeys={checkedKeys}
                expandedKeys={expandedKeys}
                onCheck={(
                  checkedKeys: Key[] | { checked: Key[]; halfChecked: Key[] },
                  { checked, checkedNodes, node, event, halfCheckedKeys }
                ) => {
                  if (Array.isArray(checkedKeys)) {
                    setTreeSelectResult((pre: any) => {
                      return {
                        ...(pre || {}),
                        [selectedParent?.que_name || ""]: (checkedKeys || [])
                          .filter((item) => item !== "全选")
                          .join(";")
                      };
                    });
                  }
                  setCheckedKeys(checkedKeys);
                }}
              />
            </div>
          </div>
          <div className="flex justify-end h-[40px] items-center">
            <Button
              size="small"
              className="mr-[8px]"
              onClick={() => setOpenSelect(false)}
            >
              取消
            </Button>
            <Button
              size="small"
              type="primary"
              className="border-none mr-[16px]"
              onClick={() => {
                setSelectedValue((pre: any) => {
                  if (Array.isArray(pre) && Array.isArray(checkedKeys)) {
                    const p = Object.values(treeSelectResult).reduce(
                      (pre: any, current: any) => {
                        return [...pre, ...(current ? current.split(";") : [])];
                      },
                      []
                    );
                    return p;
                  }
                  return pre;
                });
                setOpenSelect(false);
              }}
            >
              确认
            </Button>
          </div>
        </div>
      </div>
      <div className="h-[32px]"></div>

      {!!(selectedValue as any)?.length && (
        <div>
          <div className="mt-[5px] text-[12px] text-[#555555]">
            已选择 {(selectedValue as any).length} 个
          </div>
          {((selectedValue || []) as any).map((tag: string) => {
            let qname = "";
            Object.entries(treeSelectResult || {}).forEach((item) => {
              const [key, value]: any = item;
              if (value.indexOf(tag) > -1) {
                qname = key;
              }
            });
            return (
              <Tag
                key={tag}
                closable
                className="mt-[5px]"
                onClose={() => handleClose(tag)}
              >
                {qname}（{tag}）
              </Tag>
            );
          })}
        </div>
      )}
    </div>
  );
};
