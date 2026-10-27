import { GientechStreamReader } from "@root/src/core/components/StreamReader";
import { handleReqOrder } from "@root/src/components/AiEditor/core/operators/help";
import IndicatorEditor from "@root/src/components/IndicatorEditor/index";
import ModuleTest from "@root/src/components/ModuleTest";
import { useEffect, useState } from "react";
const reqArr = [
  {
    sectionId: "1",
    title: "（一）本次申报方案"
  },
  {
    sectionId: "2",
    title: "（二）本次申报方案说明"
  },
  {
    sectionId: "3",
    title: "（三）借款人与我行银企合作情况"
  },
  {
    sectionId: "4",
    title: "（四）借款人所在集团我行授信情况"
  },
  {
    sectionId: "5",
    title: "（五）该笔贷款是否符合我行信贷政策"
  }
];

const hasDependency = {
  "1": ["2", "3"],
  "2": ["1"],
  "4": ["3"]
};

const Demo = () => {
  const formSchema: any = [
    {
      title: "公司名称",
      dataIndex: "companyName"
    },
    { title: "所属行业", dataIndex: "profession" },
    { title: "所属行业", dataIndex: "profession1" },
    { title: "所属行业", dataIndex: "profession2" },
    { title: "所属行业", dataIndex: "profession3" },
    { title: "所属行业", dataIndex: "profession4" },
    { title: "所属行业", dataIndex: "profession5" },
    { title: "所属行业", dataIndex: "profession6" },
    { title: "所属行业", dataIndex: "profession7" }
  ];

  useEffect(() => {
    const res = handleReqOrder(reqArr, hasDependency);
  }, []);

  const [value, setValue] = useState<string>("");
  const getValue = (val: string) => {
    setValue(val);
  };
  const curData = {
    filePath:
      "http://localhost:9000/dev-rag-data/电子元器件/关于印发《电子元器件和集成电路国际交易中心股份有限公司入离职管理办法（试行）》等7项制度的通知(2).pdf/V0/关于印发《电子元器件和集成电路国际交易中心股份有限公司入离职管理办法（试行）》等7项制度的通知(2).pdf",
    fileName:
      "关于印发《电子元器件和集成电路国际交易中心股份有限公司入离职管理办法（试行）》等7项制度的通知(2).pdf",
    fileType: "pdf",
    totalPages: 59,
    token:
      "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJHSUVOLVJBRyIsImF1ZCI6IkpJQUJJTkJJTjAwIiwidXNlcklkIjoxMjQzLCJ1c2VyTmFtZSI6IkpJQUJJTkJJTjAwIiwic3ViIjoibWl4ZWRRdWFudHVtIiwiZXhwIjoxNzYzMDEzNjI4LCJpYXQiOjE3NjI5MjcyMjh9.YyqI6SYChUDhfaueHDhxrj364Lj1gB3sGvN9p8eEreM",
    annotations: [
      {
        id: "18a1744386c",
        pageNumber: 41,
        x: 0.4437,
        y: 0.2568,
        width: 0.1664,
        height: 0.0226,
        content: "",
        color: "#4FC3F7"
      },
      {
        id: "8a1744386c3",
        pageNumber: 41,
        x: 0.1227,
        y: 0.2925,
        width: 0.7546,
        height: 0.126,
        content: "",
        color: "#4FC3F7"
      },
      {
        id: "a1744386c37",
        pageNumber: 41,
        x: 0.1227,
        y: 0.4293,
        width: 0.7513,
        height: 0.0927,
        content: "",
        color: "#4FC3F7"
      },
      {
        id: "1744386c373",
        pageNumber: 41,
        x: 0.1244,
        y: 0.5327,
        width: 0.7496,
        height: 0.0559,
        content: "",
        color: "#4FC3F7"
      }
    ],
    initialPage: 41,
    initialZoom: 1
  };
  return (
    <div className="w-full h-full">
      <GientechStreamReader
        convertedFilePath={curData.filePath}
        fileName={curData.fileName}
        fileType={curData.fileType}
        initialPage={curData.initialPage}
        totalPages={curData.totalPages}
        authorization={curData.token}
        annotations={curData.annotations}
        streamApiUrl="/proxy/index/knowledgeBase/file/stream"
        eventsEmit={(name) => {
          switch (name) {
            case "viewer:close":
              //onClose();
              break;
          }
        }}
        tools={{
          close: true
        }}
      />
    </div>
  );
};

export default Demo;
