import "@/assets/styles/knowledgebase.less";
import { Tabs } from "antd";
import { useState } from "react";
import PermissionConfig from "./PermissionConfig";
import AnalysisConfig from "./AnalysisConfig";

const configTabsItems = [
  {
    key: "1",
    label: "解析配置",
  },
  {
    key: "2",
    label: "权限配置",
  },
];

export interface IConfiguration {
  kbInfo: {
    [key: string]: any;
  };
  closeDrawer: (isReFetch?: boolean) => void;
}

const Configuration = (props: IConfiguration) => {
  const [tabKey, setTabKey] = useState(configTabsItems[0].key);

  const tabChange = (key: string) => {
    setTabKey(key);
  };

  return (
    <div className="configuration-wrap bg-white">
      <div className="tabs-wrap">
        <Tabs items={configTabsItems} onChange={tabChange} activeKey={tabKey} />
      </div>
      <div className="tab-content-wrap">
        {tabKey === configTabsItems[0].key && <AnalysisConfig {...props} />}
        {tabKey === configTabsItems[1].key && <PermissionConfig />}
      </div>
    </div>
  );
};

export default Configuration;
