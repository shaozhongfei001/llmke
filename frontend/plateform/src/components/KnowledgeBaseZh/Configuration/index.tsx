import "@/assets/styles/knowledgebaseNew.less";
import { message, Tabs } from "antd";
import { useEffect, useState } from "react";
// import AnalysisConfig from "./AnalysisConfig";
import KonwledgeConfig from "./KnowledgeConfig/index";
import { useParams } from "react-router-dom";
import PermisssonConfig from "@root/src/pages/Components/PermissionConfig";
import { useServices } from "../service";

const configTabsItems = [
  {
    key: "1",
    label: "知识库配置"
  },
  {
    key: "2",
    label: "权限配置"
  }
];

export interface IConfiguration {
  kbInfo: {
    [key: string]: any;
  };
  settingOpt?: {
    [key: string]: boolean;
  };
  platform?: string;
}

const Configuration = (props: IConfiguration) => {
  const { platform } = props;
  const params = useParams();
  const [kbInfo, setKbInfo] = useState<any>({});
  const [tabKey, setTabKey] = useState(configTabsItems[0].key);
  const [drawConfig, setDrawConfig]: any = useState(null);
  const { getKbById } = useServices(platform);
  const tabChange = (key: string) => {
    setTabKey(key);
  };

  useEffect(() => {
    if (params.id) {
      setDrawConfig({ type: "permission", data: { id: params.id } });
    }
  }, [params]);

  const fetchKBDetail = async () => {
    const id = params.id;
    if (id) {
      const res = (await getKbById({ id })) as any;
      if (res) {
        const { permission } = res;
        if (permission === 0) {
          message.error("暂无操作权限，请联系管理员申请");
          return;
        }
        setKbInfo({ ...res });
      }
    }
  };

  useEffect(() => {
    // fetchKBDetail();
    setKbInfo(props.kbInfo);
  }, [params, props]);

  return (
    <div className="configuration-wrap bg-white">
      <Tabs items={configTabsItems} onChange={tabChange} activeKey={tabKey} />
      <div className="tab-content-wrap flex justify-center">
        {tabKey === configTabsItems[0].key && (
          // <>
          //   {props.settingOpt ? (
          //     <AnalysisConfig {...props} kbInfo={kbInfo} />
          //   ) : (
          //     <KonwledgeConfig kbInfo={kbInfo} fetchKBDetail={fetchKBDetail} />
          //   )}
          // </>
          <>
            <KonwledgeConfig kbInfo={kbInfo} fetchKBDetail={fetchKBDetail} platform={ platform } />
          </>
        )}
        {tabKey === configTabsItems[1].key && (
          <div className="h-full relative py-[20px]  ">
            <PermisssonConfig
              subTitle={"知识库授权范围"}
              drawConfig={drawConfig}
              type="baseRight"
              bizType={1}
              kbInfo={kbInfo}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default Configuration;
