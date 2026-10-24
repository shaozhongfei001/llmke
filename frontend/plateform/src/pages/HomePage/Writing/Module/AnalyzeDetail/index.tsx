import { useServices } from "./common/server";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import FormContent from "./components/FormContent";
import ModuleHeader from "@root/src/components/ModuleHeader";
import { ArrowLeftOutlined } from "@ant-design/icons";
import ModuleTest from "@root/src/components/ModuleTest";
import { message, Spin } from "antd";

export interface IAnalyzeDetail {
  description?: string;
  systemPrompt?: string;
  userPrompt?: string;
  name?: string;
  gmtModified?: string;
  indicators?: number[];
}

function AnalyzeDetail() {
  const { getAnalysisDetail, updateAnalyzer } = useServices();
  const navigator = useNavigate();

  const { id } = useParams();

  const queryAnalysisDetailById = useQuery({
    queryKey: ["getAnalysisDetail", id],
    queryFn: () => getAnalysisDetail(id as string),
    enabled: !!id
  });

  const [detailData, setDetailData] = useState({
    name: "未命名组件",
    description: "未保存",
    systemPrompt: "",
    gmtModified: "",
    userPrompt: "",
    id,
    categoryId: "",
    indicatorList: []
  });
  const [formSchema, setFormSchema] = useState<any>([]);

  useEffect(() => {
    if (!queryAnalysisDetailById.data) return;
    const {
      name,
      description,
      systemPrompt,
      gmtModified,
      userPrompt,
      id,
      categoryId,
      indicatorList = []
    } = queryAnalysisDetailById.data;

    setDetailData({
      name,
      description,
      systemPrompt,
      gmtModified,
      userPrompt,
      id,
      categoryId,
      indicatorList
    });
  }, [queryAnalysisDetailById.data]);

  const updateInfoById = async (params: IAnalyzeDetail) => {
    if (!id) {
      message.error("id不存在");
      return;
    }
    const res: any = await updateAnalyzer.mutateAsync({
      ...params,
      id: id
    });
    if (res && res.success) {
      return res;
    } else {
      false;
    }
  };

  const handleNameChange = async (name: string) => {
    const res = await updateInfoById({ name });
    res && message.success("标题修改成功");
  };

  return (
    <Spin
      spinning={queryAnalysisDetailById.isLoading}
      className="h-[calc(100vh-60px)]"
      tip="Loading"
    >
      <div className="h-[calc(100vh-60px)] w-[100vw] overflow-hidden fixed top-[60px] left-0">
        <header
          className="h-[66px] box-border bg-[#FCFDFF] py-3 pl-[28px]"
          style={{
            borderBottom: "1px solid #EEE",
            borderTop: "1px solid #EEE"
          }}
        >
          <div className="h-full flex items-center">
            <span className="inline-block mr-[16px]">
              <ArrowLeftOutlined
                style={{
                  fontSize: "20px",
                  color: "#2468F2",
                  cursor: "pointer"
                }}
                onClick={() => {
                  let posInfo: any = {};
                  if (detailData.id && detailData.categoryId) {
                    posInfo = {
                      id: detailData.id,
                      categoryId: detailData.categoryId
                    };
                  }
                  navigator("/docWriting/component/analyze", {
                    state: posInfo
                  });
                }}
              />
            </span>
            <ModuleHeader {...detailData} handleNameChange={handleNameChange} />
          </div>
        </header>
        <div className="h-[calc(100%-66px)] box-border flex bg-white">
          <div className="w-1/2 h-[calc(100%-25px)]">
            <FormContent
              {...detailData}
              setDetailData={setDetailData}
              updateInfoById={updateInfoById}
              setFormSchema={setFormSchema}
            />
          </div>
          <div className="w-1/2 h-full bg-[#E9ECFF] rounded-s-[12px]">
            <ModuleTest
              formSchema={formSchema}
              mouduleName="ANALYSIS"
              testId={id as string}
            />
          </div>
        </div>
      </div>
    </Spin>
  );
}

export default AnalyzeDetail;
