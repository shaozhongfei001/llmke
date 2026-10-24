import React, { useState, useEffect, useMemo } from "react";
import { message } from "antd";
import { ReactComponent as KnowledgeConf } from "@/assets/svg/konwledgeConf.svg";
import { ReactComponent as FAQConf } from "@/assets/svg/faqConfig.svg";
import { ReactComponent as GraphConf } from "@/assets/svg/graphConfig.svg";
import { FILE_BTN, getBtnDisabled } from "@root/src/const/permission";
import GraphConfig from "./GraphConf";
import FAQConfig from "./FAQConf";
import ParseConfig from "./ParseConf";
import { updateConf } from "../service";
import {
  getEmbeddingModels,
  getModels,
  getMultiModels
} from "../../KnowledgeAnalyBlock/service";
const configList = [
  {
    label: "知识解析配置",
    key: 1,
    icon: <KnowledgeConf width={16} />
  },
  {
    label: "FAQ配置",
    key: 2,
    icon: <FAQConf width={16} />
  },
  {
    label: "图谱增强配置",
    key: 3,
    icon: <GraphConf width={16} />
  }
];

// platform作为写作与问答业务的区分，同时也是service中接口请求的区分
const KonwledgeConfig = ({ kbInfo, fetchKBDetail, platform="rag-qa" }: any) => {
  const [activeKey, setActiveKey] = useState(configList[0].key);
  const [btnLoading, setBtnLoading] = useState(false);

  // 模型选择下拉框
  const [embeddingModelsOption, setEmbeddingModelsOption] = useState([]);
  const [modelsOption, setModelsOption] = useState([]);
  const [multiModelsOption, setMultiModelsOption] = useState([]);

  useEffect(() => {
    getOptions();
  }, []);

  const getOptions = async () => {
    try {
      const [EmbeddingModelsRes, modelsRes, multiModelRes] =
        await Promise.allSettled([
          getEmbeddingModels(),
          getModels(),
          getMultiModels()
        ]);
      if (
        EmbeddingModelsRes.status === "fulfilled" &&
        EmbeddingModelsRes.value
      ) {
        setEmbeddingModelsOption(handleOptions(EmbeddingModelsRes));
      }

      if (multiModelRes.status === "fulfilled" && multiModelRes.value) {
        setMultiModelsOption(handleOptions(multiModelRes));
      }

      if (modelsRes.status === "fulfilled" && modelsRes.value) {
        setModelsOption(handleOptions(modelsRes));
      }
    } catch (error) {
      console.log("error", error);
    }
  };

  const handleOptions = (res: any) => {
    return (res.value.records || []).map((o: any) => ({
      label: o.modelName,
      value: o.modelName
    }));
  };

  const updateConfFn = async (data: any) => {
    try {
      setBtnLoading(true);
      const res = await updateConf({
        ...data,
        id: kbInfo.id,
        fileFaqMaxNums:
          data?.fileFaqMaxNums === Infinity ? 0 : data.fileFaqMaxNums
      });
      setBtnLoading(false);
      if (res) {
        message.success("保存解析配置成功");
        fetchKBDetail();
      }
    } catch (e) {
      message.success("保存解析配置失败");
      console.log(e);
      setBtnLoading(false);
    }
  };

  const disabled = getBtnDisabled(FILE_BTN.ANALYSIS_CONFIG, kbInfo.permission);

  const realConfigList = useMemo(() => { 
    return platform === "intelbrain-dw"
    ? [configList[0]]
    : configList;
  },[platform])

  return (
    <div className="w-full flex flex-row h-[calc(100%-50px)] parser-config">
      <div
        className="w-[200px] h-full py-[20px] pr-[12px]"
        style={{ borderRight: "1px solid #EEEEEE" }}
      >
        {realConfigList.map((c) => {
          return (
            <div
              key={c.key}
              className="flex flex-row h-[40px] items-center px-[12px] cursor-pointer"
              style={{
                color: activeKey == c.key ? "#055AFF" : "#2A2A2A",
                backgroundColor: activeKey == c.key ? "#F1F5FF" : "#FFFFFF"
              }}
              onClick={() => setActiveKey(c.key)}
            >
              {c.icon}
              <span className="ml-[10px]">{c.label}</span>
            </div>
          );
        })}
      </div>
      <div
        className={`w-full h-full min-h-[300px] flex justify-center overflow-y-auto`}
        style={{
          backgroundColor: activeKey == 3 ? "#fff" : "#F9F9F9"
        }}
      >
        {activeKey == 1 && (
          <ParseConfig
            btnLoading={btnLoading}
            save={updateConfFn}
            disabled={disabled}
            kbInfo={kbInfo}
            embeddingModelsOption={embeddingModelsOption}
            multiModelsOption={multiModelsOption}
            modelsOption={modelsOption}
            platform={ platform }
          />
        )}
        {activeKey == 2 && (
          <FAQConfig
            btnLoading={btnLoading}
            save={updateConfFn}
            disabled={disabled}
            kbInfo={kbInfo}
            modelsOption={modelsOption}
          />
        )}
        {activeKey == 3 && (
          <GraphConfig
            btnLoading={btnLoading}
            save={updateConfFn}
            disabled={disabled}
            kbInfo={kbInfo}
            modelsOption={modelsOption}
          />
        )}
      </div>
    </div>
  );
};

export default KonwledgeConfig;
