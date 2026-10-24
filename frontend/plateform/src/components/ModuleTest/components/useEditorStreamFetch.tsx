import { fetchEventSource } from "@microsoft/fetch-event-source";
import { getTokenLocal } from "@root/src/apis/token";
import { message } from "antd";
import { useEffect, useRef, useState } from "react";
const mockList = [
  {
    metadata: {
      source:
        "dev-rag-data/intelbrain-dw/1243/遂宁知识库/遂宁知识库_公司简介遂宁睿杰兴doc/V0/公司简介-遂宁睿杰兴.pdf",
      file_path:
        "dev-rag-data/intelbrain-dw/1243/遂宁知识库/遂宁知识库_公司简介遂宁睿杰兴doc/V0/公司简介-遂宁睿杰兴.pdf",
      id: "ZGV2LXJhZy1kYXRhL2ludGVsYnJhaW4tZHcvMTI0My/pgYLlroHnn6Xor4blupMv6YGC5a6B55+l6K+G5bqTX+WFrOWPuOeugOS7i+mBguWugeedv+adsOWFtGRvYy9WMC/lhazlj7jnroDku4st6YGC5a6B552/5p2w5YW0LnBkZg==",
      search_type: ["milvus", "es"],
      offset: [
        [0, 13],
        [14, 169],
        [170, 288],
        [289, 343],
        [344, 409],
        [410, 420],
        [421, 463],
        [464, 503],
        [504, 514],
        [515, 539],
        [14, 169],
        [170, 288],
        [289, 343],
        [344, 409],
        [410, 420],
        [421, 463],
        [464, 503]
      ],
      pic_offset_list: [],
      pic_children_id_list: [],
      text_parent_id_list: [],
      chunk_type: "text",
      position:
        "[[[367, 310], [791, 310], [791, 350], [367, 350]], [[136, 385], [1024, 385], [1024, 541], [136, 541]], [[136, 543], [1022, 543], [1022, 737], [136, 737]], [[138, 757], [1018, 757], [1018, 844], [138, 844]], [[136, 864], [1018, 864], [1018, 1006], [136, 1006]], [[191, 1026], [478, 1026], [478, 1056], [191, 1056]], [[185, 1079], [1018, 1079], [1018, 1107], [185, 1107]], [[183, 1129], [1016, 1129], [1016, 1159], [183, 1159]], [[193, 1224], [476, 1224], [476, 1257], [193, 1257]], [[185, 1279], [945, 1279], [945, 1307], [185, 1307]], [[136, 385], [1024, 385], [1024, 541], [136, 541]], [[136, 543], [1022, 543], [1022, 737], [136, 737]], [[138, 757], [1018, 757], [1018, 844], [138, 844]], [[136, 864], [1018, 864], [1018, 1006], [136, 1006]], [[191, 1026], [478, 1026], [478, 1056], [191, 1056]], [[185, 1079], [1018, 1079], [1018, 1107], [185, 1107]], [[183, 1129], [1016, 1129], [1016, 1159], [183, 1159]]]",
      file_id: "65338",
      image_path: "",
      page_size:
        "[[1191, 1684], [1191, 1684], [1191, 1684], [1191, 1684], [1191, 1684], [1191, 1684], [1191, 1684], [1191, 1684], [1191, 1684], [1191, 1684], [1191, 1684], [1191, 1684], [1191, 1684], [1191, 1684], [1191, 1684], [1191, 1684], [1191, 1684]]",
      page_number: [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
      chunk_index: -1
    },
    order_num: "4420361811611142897",
    page_content:
      "遂宁睿杰兴科技有限公司简介\n遂宁睿杰兴科技有限公司隶属于睿杰鑫集团，于2021年入驻遂宁经开区，公司集研发设计、加工、销售、外贸为一体，专业从事双面、多层线路板、高密度互连电路（HDI）板及特种印制线路板的制造。产品广泛应用于通讯、网控、数码消费、手机、高端LED、工业控制、安防、仪器仪表、汽车电子等领域，制程能力年产能在90万平方米。\n公司于入驻同年上规并荣获遂宁2021年“优秀成长型企业”荣誉称号。现已通过IS09001：2015、IS014001：2015、IATF16949、UL、CQC等体系认证。成为科陆、海信、创维、小米、紫光、亿联、聚利等客户的优质供应商。\n公司产品交付时间：双面板打样最快48小时交付，批量最快7天交付；多层板打样最快4天交付，批量最快10天交付。\n公司拥有优秀的制造、销售、管理团队并坚持“精益生产、品质为先、客户至上、持续改善”的经营理念为客户提供优质的产品和持续改进的服务。\n深圳市场开发服务中心\n电话：0755-23804248／83102887 传真：0755-23804247\n地址：深圳市宝安区西乡街道黄田光汇工业园A栋 邮箱：pcb＠mzrjx.com",
    parsedFilePath:
      "http://10.15.12.13:9000/dev-rag-data/intelbrain-dw/1243/遂宁知识库/遂宁知识库_公司简介遂宁睿杰兴doc/V0/公司简介-遂宁睿杰兴.pdf",
    pdfPages: 1,
    pic_url_list: [],
    score: "0.26666666666666666",
    type: "Document"
  }
];

enum LLMStatus {
  Normal = 1,
  Success,
  Error
}

interface SectionTestApi {
  signal?: AbortSignal;
  params: any;
  id: number | string;
  onmessage: (ev: any) => any;
  onerror?: (err: any) => any;
  onclose?: () => any;
}

const api_sectionTest = (data: SectionTestApi, type = "SECTION") => {
  const token = getTokenLocal();
  const { onmessage, onerror, signal, onclose, id } = data;
  const isSection = type === "SECTION";
  const eventSourceUrl = isSection
    ? `/cecProxy/dw/article/component/section/${id}/test`
    : `/cecProxy/dw/component/analysis/${id}/test`;

  // 实际的 fetchEventSource 请求
  fetchEventSource(eventSourceUrl, {
    openWhenHidden: true,
    signal,
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: token
    },
    body: JSON.stringify(data.params),
    onmessage,
    onerror,
    onclose
  });
};

// 处理流式接口返回的文本
const delThinkTag = (text: string) => {
  // 使用正则表达式去除 <think> 及其后面的数据或被 <think></think> 包裹的数据
  const cleanedBuffer = text.replace(/<think>.*?<\/think>|<think>.*$/gs, "");
  return cleanedBuffer;
};

// 流式请求相关
const useEditorStreamFetch = (
  testId: number | string,
  mouduleName: "SECTION" | "ANALYSIS"
) => {
  // 当前段落内容
  const [mdData, setMdData] = useState<string>("");
  // 当前溯源内容
  const [selectFile, setSelectFile] = useState<any>("");
  // 保存当前所有的溯源文件
  // const [allFile, setAllFile] = useState<any[]>(mockList);
  const [allFile, setAllFile] = useState<any[]>();
  // loading
  const [wirteLoading, setWriteLoading] = useState(false);
  // 用于缓冲数据，可以理解为流式数据的节流处理，保证渲染性能
  const bufferStringRef = useRef<string>("");
  // 定时器引用，用于同步缓冲区的数据
  const syncIntervalRef = useRef<number | null>(null);
  // 用于取消请求
  const sseController = useRef(new AbortController());
  // 停止生成
  const stopGen = () => {
    stopSyncBuffer();
    sseController.current.abort();
    sseController.current = new AbortController();
  };

  // 启动定时器，每 300 毫秒同步一次缓冲数据
  const startSyncBuffer = () => {
    syncIntervalRef.current = setInterval(() => {
      if (bufferStringRef.current) {
        if (bufferStringRef.current.includes("</think>")) {
          setWriteLoading(false);
        } else if (
          !bufferStringRef.current.includes("</think>") &&
          !bufferStringRef.current.includes("<think>")
        ) {
          setWriteLoading(false);
        }
        setMdData((_) => delThinkTag(bufferStringRef.current));
      }
    }, 300);
  };

  // 清除定时器并同步剩余数据
  const stopSyncBuffer = () => {
    if (syncIntervalRef.current) {
      clearInterval(syncIntervalRef.current);
      syncIntervalRef.current = null;
    }
    if (bufferStringRef.current) {
      // 试用版中间变量，避免多次stopSyncBuffer造成的异步访问bufferStringRef.current数据为空的问题
      const text = bufferStringRef.current;
      setMdData((_) => {
        return delThinkTag(text);
      });
      bufferStringRef.current = ""; // 清空缓冲区
    }
  };

  const handleRagReCallFile = (docs: any) => {
    let _docs: any = docs;
    if (typeof _docs === "string") {
      _docs = JSON.parse(_docs);
    }
    setAllFile(_docs);
  };

  const onmessage = ({ data }: { data: string }) => {
    const { docs, reply, status } = JSON.parse(data);
    const curChunkString = (reply || {})?.content || "";
    switch (status) {
      case LLMStatus.Success:
        setWriteLoading(false);
        // 释放缓冲区
        stopSyncBuffer();
        handleRagReCallFile(docs);
        break;
      case LLMStatus.Error:
        // 释放缓冲区
        message.error(curChunkString);
        setWriteLoading(false);
        stopSyncBuffer();
        break;
      case LLMStatus.Normal:
        // 将数据追加到缓冲区
        bufferStringRef.current += curChunkString;
        break;
      default:
        message.warning("返回状态异常");
        break;
    }
  };

  const onclose = () => {
    // 释放缓冲区
    stopSyncBuffer();
  };

  const onerror = (ev: any) => {
    // 释放缓冲区
    stopSyncBuffer();
    setWriteLoading(false);
    message.error("请求出错，请联系管理员");
    console.log(ev);
    throw ev;
  };

  const submitFormData = (formData: any) => {
    if (!testId) {
      message.error("id不存在，请联系管理员");
      return;
    }
    // 清空溯源文件
    setAllFile([]);
    // 清空原有数据
    setMdData("");
    // loading
    setWriteLoading(true);
    // 打开缓冲区，开始同步数据
    startSyncBuffer();
    // 发送请求
    api_sectionTest(
      {
        onmessage,
        onerror,
        signal: sseController.current.signal,
        onclose,
        // id: 17,
        id: testId,
        params: formData
      },
      mouduleName
    );
  };
  return {
    submitFormData,
    selectFile,
    setSelectFile,
    mdData,
    allFile,
    wirteLoading,
    stopGen
  };
};
export default useEditorStreamFetch;
