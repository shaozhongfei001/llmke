import KnowledgeBase from "@/components/KnowledgeBaseZh";
import { Tabs } from "antd";
import { useEffect, useState } from "react";
import Database from "./compoments/Database";
import { useLocation } from "react-router-dom";

const items = [
  {
    key: "1",
    label: "文件管理"
  },
  {
    key: "2",
    label: "数据库管理"
  }
];

const ResourceM = () => {
  const location = useLocation();
  const [activeKey, setActiveKey] = useState("1");

  const tabChange = (key: string) => {
    setActiveKey(key);
  };

  useEffect(() => {
    if (
      !location.state ||
      !location.state.currentTab ||
      location.state.currentTab !== "db"
    )
      return;
    setActiveKey("2");
  }, [location]);

  return (
    <>
      <div
        style={{
          fontFamily: `Microsoft YaHei`,
          fontSize: "16px",
          fontWeight: 700,
          marginBottom: 16
        }}
      >
        素材管理
      </div>
      <div className="bg-white h-[calc(100%-50px)] rounded-[8px]">
        <div className="custom-tab-box px-5">
          <Tabs
            defaultActiveKey="1"
            items={items}
            onChange={tabChange}
            activeKey={activeKey}
          />
        </div>
        {activeKey === "1" && (
          <KnowledgeBase
            title="hide"
            konwledgeTitlesTab={"hide"}
            selectOpt={[
              { value: 1, label: "我的素材" },
              { value: 2, label: "共享素材" }
            ]}
            pathPrefix="/docWriting/resource"
            platform="intelbrain-dw"
          />
        )}
        {activeKey === "2" && <Database />}
      </div>
    </>
  );
};
export default ResourceM;
