import { Flex, Tooltip, Tree } from "antd";
import { CloseOutlined } from "@ant-design/icons";
import { useEffect, useMemo, useState } from "react";
import { useStateStore } from "@root/src/components/AiEditor/core/states/useStateStore";
import { ModueEnum } from "../../@types/sys";
import OutlinesIcon from "@root/src/components/AiEditor/assets/icon/outlines.svg";
import "./style.less";

export const Catalogue = () => {
  const { projectData, open, writingSettingOpen } = useStateStore();

  const [close, setClose] = useState(true);
  const handleClose = () => {
    setClose(!close);
  };

  const outlineData = useMemo(() => {
    if (!projectData.outlines) return [];
    // 递归处理子段落
    const processSubParagraphs = (items: any[], deep = 1) => {
      return items.map((item, index) => {
        const node: any = {
          title: item.title,
          key: item.id,
          deep,
        };

        // 如果有子段落，递归处理
        if (item.subParagraphs && item.subParagraphs.length > 0) {
          node.children = processSubParagraphs(item.subParagraphs, deep + 1);
        }

        return node;
      });
    };

    // 如果 outlines 是对象（单个大纲），将其包装成数组处理
    const outlinesArray = Array.isArray(projectData.outlines)
      ? projectData.outlines
      : [projectData.outlines];

    return processSubParagraphs(outlinesArray);
  }, [projectData.outlines]);

  //   打开右边sider,隐藏大纲
  useEffect(() => {
    if (projectData.currentModule !== ModueEnum.Writing && open) setClose(true);
  }, [projectData.currentModule, open]);

  const handleClick = (key: string) => {
    const targetElement = document.getElementById(key);
    targetElement &&
      targetElement.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  return (
    <>
      {!writingSettingOpen && !!projectData.generateType && (
        <>
          {close ? (
            <Tooltip placement="right" title={"大纲"}>
              <div
                className="fixed w-8 h-8 p-2 box-border rounded-r-md text-xs top-[180px]  bg-white cursor-pointer z-20"
                onClick={handleClose}
              >
                <img src={OutlinesIcon} width={16} alt="" />
              </div>
            </Tooltip>
          ) : (
            <Flex
              vertical
              className="fixed h-[calc(100vh-180px)] left-0 top-[150px] overflow-y-auto z-20 mt-5 px-4 w-[240px] max-w-[270px] box-border"
            >
              <Flex
                justify="space-between"
                className="pb-2 w-full h-[40px]"
                style={{
                  borderBottom: "1px solid #D9D9D9",
                }}
              >
                <span className="text-[#000] text-[16px]">大纲</span>
                <CloseOutlined onClick={handleClose} />
              </Flex>
              <div className="font-bold text-[#555] py-1 mt-[17px] h-[32px] text-ellipsis w-full whitespace-nowrap overflow-hidden">
                {projectData.title}
              </div>
              <div className="flex-1 overflow-y-auto">
                <Tree
                  treeData={outlineData}
                  className="bg-[rgb(0,0,0,0)] text-[13px] catalogue"
                  defaultExpandAll={true}
                  titleRender={(nodeData) => (
                    <span
                      id={`#${nodeData.key}`}
                      onClick={() => {
                        handleClick(nodeData.key);
                      }}
                      style={{
                        display: "inline-block",
                        width: `${208 - nodeData.deep * 16}px`,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {nodeData.title}
                    </span>
                  )}
                />
              </div>
            </Flex>
          )}
        </>
      )}
    </>
  );
};

export default Catalogue;
