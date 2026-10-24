import { Button, Drawer, Input, Switch, Empty } from "antd";
import { useState, useEffect, useMemo } from "react";
import { CloseOutlined, PlusOutlined } from "@ant-design/icons";
import aiphoto from "@/assets/img/aiRobit.png";
import aiphotoDis from "@/assets/img/aiRobitDis.png";
import genera from "@/assets/gif/genera.gif";
import { uid } from "uid";
import OutlineItem from "./OutlineItem";

const { TextArea } = Input;

export enum outlineChangeTypes {
  delNode = "delNode",
  configSection = "configSection",
  editTitle = "editTitle"
}

type outlineChangeData = {
  node: any;
  title?: string;
};

interface Iprops {
  outLineData: any[];
  isShow?: boolean;
  helpLoading?: boolean;
  setChecked: (check: boolean) => void;
  setOutLineData: (data: any[]) => void;
  handleAIHelper: () => void;
}

const OutLines = (props: Iprops) => {
  const {
    outLineData,
    isShow = false,
    helpLoading = false,
    setOutLineData,
    setChecked,
    handleAIHelper
  } = props;
  const [open, setOpen] = useState(false);
  const [curNodeId, setCurNodeId] = useState<number | string>("");
  const [editNodeId, setEditNodeId] = useState<string | undefined>(undefined);

  const addRow = () => {
    setOutLineData([...outLineData, { id: uid() }]);
  };

  const toggleOutline = (v: boolean) => {
    setChecked(v);
  };

  const onOutlinesChangeHandler = (
    type: outlineChangeTypes,
    cfg: outlineChangeData
  ) => {
    const { node, title } = cfg;
    const { id } = node;
    switch (type) {
      case outlineChangeTypes.delNode:
        delNodeHandler(id);
        break;
      case outlineChangeTypes.configSection:
        console.log("edit node:", node);
        setCurNodeId(id);
        setOpen(true);
        break;
      case outlineChangeTypes.editTitle:
        if (title) {
          editTitleHandler(id, title);
        }
        break;
    }
  };

  const editNodeIdChangeHandler = (nodeId: string | undefined) => {
    setEditNodeId(nodeId);
  };

  const editTitleHandler = (nodeId: string, title: string) => {
    const _outlinesCopy = editTitleById(outLineData, nodeId, title);
    setOutLineData([..._outlinesCopy]);
  };

  const editTitleById = (
    treeData: any[],
    targetId: string | number,
    title: string
  ) => {
    const list: any[] = [];
    treeData.forEach((i: any) => {
      const _i = { ...i };
      if (_i.id === targetId) {
        _i.title = title;
      }
      list.push({ ..._i });
    });
    return list;
  };

  const delNodeHandler = async (nodeId: string | number) => {
    const _outlinesCopy = deleteNodeById(outLineData, nodeId);
    setOutLineData([..._outlinesCopy]);
  };

  const deleteNodeById = (treeData: any[], targetId: string | number) => {
    const list: any[] = [];
    treeData.forEach((i: any) => {
      if (i.id !== targetId) {
        list.push({ ...i });
      }
    });
    return list;
  };

  const closeIptHandler = (e: MouseEvent) => {
    const _target: any = e.target;

    const findElIsIpt = (el: any) => {
      const { nodeName, parentNode } = el;
      if (nodeName !== "BODY") {
        if (["SPAN", "INPUT"].includes(nodeName)) {
          if (el.className.includes("node-title-ipt")) {
            console.log(el, editNodeId);
            return true;
          }
        }
        if (parentNode) {
          return findElIsIpt(parentNode);
        }
      }
      return false;
    };

    if (!findElIsIpt(_target)) {
      editNodeIdChangeHandler(undefined);
    }
  };

  const closeDrawerShow = () => {
    setCurNodeId("");
    setOpen(false);
  };

  const contentOnChangeHandler = (e: any) => {
    const content = e.target.value.trim();

    const _outlinesCopy = contentOnChange(outLineData, curNodeId, content);
    setOutLineData([..._outlinesCopy]);
  };

  const contentOnChange = (
    treeData: any[],
    targetId: string | number,
    content: string
  ) => {
    const list: any[] = [];
    treeData.forEach((i: any) => {
      const _i = { ...i };
      if (_i.id === targetId) {
        _i.contentAbstract = content;
      }
      list.push({ ..._i });
    });
    return list;
  };

  const contentAbstract = useMemo(() => {
    let str = "";
    if (curNodeId) {
      const item = outLineData.find((i: any) => i.id === curNodeId);
      if (item) {
        str = item.contentAbstract;
      }
    }
    return str;
  }, [curNodeId, outLineData]);

  useEffect(() => {
    window.addEventListener("click", closeIptHandler);
    return () => {
      window.removeEventListener("click", closeIptHandler);
    };
  }, []);

  return (
    <>
      <div className="flex justify-between mb-3">
        <div className="text-gray-2a text-base pt-1">
          <b className="mr-2">大纲</b>
          <Switch value={isShow} onChange={toggleOutline} />
        </div>
        <div className="flex gap-2">
          <Button
            className={`${isShow ? "text-primary-color" : "text-[#bbb]"} text-sm px-2`}
            onClick={handleAIHelper}
            disabled={!isShow}
            icon={
              <img
                className="pt-1"
                src={!isShow ? aiphotoDis : helpLoading ? genera : aiphoto}
                width={20}
                height={24}
              />
            }
          >
            AI帮写
          </Button>
          <Button
            className={`${isShow ? "text-primary-color" : "text-[#bbb]"} text-sm px-2`}
            disabled={!isShow}
            icon={<PlusOutlined />}
            onClick={addRow}
          >
            添加标题
          </Button>
        </div>
      </div>
      {/* <div>{JSON.stringify(outLineData)}</div> */}
      <div className={`${isShow ? "" : "hidden"}`}>
        <div className="flex h-11 leading-[44px] bg-[#fafafa] border-0 border-b border-solid border-[#eee] px-3 text-gray-2a text-sm">
          <div className="flex-1">标题</div>
          <div className="w-28 pl-3">操作</div>
        </div>
        {outLineData.length ? (
          outLineData.map((rootNode: any, idx: number) => {
            return (
              <OutlineItem
                key={`${rootNode.id}-outline-${idx}`}
                node={rootNode}
                editNodeId={editNodeId}
                onOutlinesChangeHandler={onOutlinesChangeHandler}
                editNodeIdChangeHandler={editNodeIdChangeHandler}
              />
            );
          })
        ) : (
          <Empty className="mt-10" />
        )}
      </div>
      <Drawer
        title={
          <div className="flex justify-between">
            <span>编辑写作配置</span>
            <CloseOutlined
              className="cursor-pointer"
              onClick={closeDrawerShow}
            />
          </div>
        }
        closeIcon={false}
        onClose={closeDrawerShow}
        open={open}
        width={430}
      >
        <div className="mb-3">内容要求</div>
        <TextArea
          showCount
          maxLength={500}
          placeholder="请输入内容要求"
          style={{ height: 120, resize: "none" }}
          value={contentAbstract}
          onChange={contentOnChangeHandler}
        />
      </Drawer>
    </>
  );
};

export default OutLines;
