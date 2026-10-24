import { useEffect, useState } from "react";

import { Layout, Menu } from "antd";
import { useStateStore } from "../../core/states/useStateStore";
import { ModueEnum } from "../../@types/sys";
import WritingModule from "./WritingModule";
import ReviewModule from "./ReviewModule";
import MaterialModule from "./MaterialModule";
import { useDataTransformer } from "../../core/useDataTransformer";
import ModulesWraper from "./ModulesWraper";
import "./index.css";
import Capsule from "./components/Capsule";
import useAiEditorOperators from "../../core/operators/useAiEditorOperators";
import { redTitleStyle } from "../MainEditor/default_style";

const { Sider } = Layout;
const closeSize = 0;
const Sidebar = () => {
  const {
    projectData,
    setProjectData,
    setDisplayOriginTemp,
    open,
    setOpen,
    mainEditor,
    setEditorManager,
  } = useStateStore();
  const { insertDataToTemp } = useAiEditorOperators();
  const [sidebarWidth, setSidebarWidth] = useState(0); // 初始宽度为460px

  useEffect(() => {
    if (projectData.currentModule !== ModueEnum.Writing) {
      setProjectData((p) => ({
        ...p,
        saveArticle: "init",
      }));
    }
  }, [projectData.currentModule]);

  // 初始化样式，没有文章内容的时候显示格式模板
  // useEffect(() => {
  //   if (
  //     projectData.customized_style &&
  //     projectData.customized_style.enable &&
  //     !projectData.article_content
  //   ) {
  //     setTimeout(() => {
  //       insertDataToTemp(
  //         mainEditor.current,
  //         {
  //           ...projectData.extraParams,
  //           title: projectData.title,
  //         },
  //         projectData.customized_style?.htmlSchema,
  //         projectData.customized_style.formSchemaMap
  //       );
  //     }, 0);
  //   }
  // }, [
  //   projectData.customized_style?.enable,
  //   projectData.article_content,
  //   projectData.extraParams,
  //   projectData.title,
  // ]);

  // 有自定义样式的情况下，使用自定义样式
  // useEffect(() => {
  //   if (projectData.customized_style && projectData.customized_style.enable) {
  //     setEditorManager((p) => ({
  //       ...p,
  //       styles: projectData?.customized_style.styles,
  //     }));
  //   } else if (projectData.article_type_mode == "1") {
  //     setEditorManager((p) => ({ ...p, styles: redTitleStyle }));
  //   }
  // }, [projectData.customized_style?.enable]);

  const handleMenuOnClick = (i) => {
    setDisplayOriginTemp(false);
    setProjectData((pre) => {
      if (i.key !== pre.currentModule) {
        setOpen((p) => {
          if (!p) {
            return true;
          }
          return p;
        });
      } else {
        setOpen((p) => !p);
      }
      return {
        ...pre,
        currentModule: i.key,
      };
    });
  };

  // 项目改版，写作模块的siderBar隐藏，但是里面涉及到的初始化代码还需要，暂不删除
  useEffect(() => {
    setSidebarWidth(
      open && projectData.currentModule !== ModueEnum.Writing ? 400 : 0
    );
  }, [open, projectData.currentModule]);

  return (
    <>
      {(!open || projectData.currentModule === ModueEnum.Writing) && (
        <Capsule />
      )}
      <Sider
        width={open ? sidebarWidth : closeSize}
        collapsedWidth={closeSize}
        style={{
          // backgroundColor: '#04336B',
          backgroundColor: "#fff",
        }}
        className="relative justify-end sider-box"
      >
        {/* <Menu
          defaultSelectedKeys={[projectData.currentModule]}
          // defaultOpenKeys={['sub1']}
          onClick={handleMenuOnClick}
          mode="inline"
          theme="light"
          inlineIndent={17}
          className="self-end"
          style={{
            width: closeSize,
            paddingLeft: 0,
          }}
          // inlineCollapsed={true}
          items={modulesToMenuData(modules, projectData.currentModule)}
        ></Menu> */}
        {/* {projectData.currentModule &&
          projectData.currentModule === ModueEnum.Writing && (
            <ModulesWraper open={open}>
              <WritingModule />
            </ModulesWraper>
          )} */}
        {projectData.currentModule &&
          projectData.currentModule === ModueEnum.Review && (
            <ModulesWraper open={open}>
              <ReviewModule />
            </ModulesWraper>
          )}
        {projectData.currentModule &&
          projectData.currentModule === ModueEnum.Material && (
            <ModulesWraper open={open}>
              <MaterialModule />
            </ModulesWraper>
          )}
        {/* 由于响应式设计兼容问题，暂不开放支持 */}
        {/* <div
        className="h-full absolute top-0 left-0 z-[200]"
        style={{
          width: '3px',
          cursor: 'col-resize',
          backgroundColor: 'transparent',
        }}
        ref={dragHandleRef}
        onMouseDown={handleMouseDown}
      /> */}
      </Sider>
    </>
  );
};

export default Sidebar;
