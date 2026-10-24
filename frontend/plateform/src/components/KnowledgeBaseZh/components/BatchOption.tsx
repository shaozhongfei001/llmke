import {
  CheckCircleOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined
} from "@ant-design/icons";
import IconDisabled from "@/assets/knowledgebase/icon-disabled.svg";
import IconDelete from "@/assets/knowledgebase/icon-delete.svg";
import { tabItems } from "@/const/knowledgebase";
import Dissolve from "@/assets/img/dissolve.png";
import Transfer from "@/assets/img/transfer.png";
import CreateSet from "@/assets/img/createSet.png";

const splitLine = {
  label: <span className="selet-option-split-line"></span>,
  title: "",
  options: []
};

const imgStyle = {
  marginRight: "6px",
  color: "#333",
  position: "relative",
  top: "2px",
  fontSize: "12px"
} as any;

export enum batchType {
  PARSE_ALL = "parse_all",
  PARSE = "parse",
  STOP = "stop",
  ENABLE = "enable",
  DISABLE = "disable",
  DELETE = "delete",
  SOURCE = "source",
  CREATE_SET = "create_set",
  TRANSFER = "transfer",
  DISSOLVE = "dissolve",
  BATCH_TRANSFER = "batch_transfer"
}

export const batchlist = [
  {
    icon: (
      <PlayCircleOutlined style={{ marginRight: "8px", color: "#014DDF" }} />
    ),
    text: "批量解析",
    value: batchType.PARSE,
    tabKey: tabItems[0].key
  },
  {
    icon: (
      <PlayCircleOutlined style={{ marginRight: "8px", color: "#014DDF" }} />
    ),
    text: "批量抽取",
    value: batchType.PARSE,
    tabKey: tabItems[1].key
  },
  {
    icon: (
      <PlayCircleOutlined style={{ marginRight: "8px", color: "#014DDF" }} />
    ),
    text: "解析所有",
    value: batchType.PARSE_ALL,
    tabKey: tabItems[0].key
  },
  {
    icon: (
      <PlayCircleOutlined style={{ marginRight: "8px", color: "#014DDF" }} />
    ),
    text: "抽取所有",
    value: batchType.PARSE_ALL,
    tabKey: tabItems[1].key
  },
  {
    icon: <img src={Transfer} className="mr-[8px]" />,
    text: "批量转移",
    value: batchType.BATCH_TRANSFER
  },
  // {
  //   icon: <img src={Transfer} className="mr-[8px]" />,
  //   text: "转移到",
  //   value: batchType.TRANSFER,
  //   isVersionShow: true
  // },
  {
    icon: <img src={CreateSet} className="mr-[8px]" />,
    text: "创建集合",
    value: batchType.CREATE_SET,
    isVersionShow: true
  },
  {
    icon: <img src={Dissolve} className="mr-[8px]" />,
    text: "解散",
    value: batchType.DISSOLVE,
    isVersionShow: true
  },
  // {
  //   icon: (
  //     <PauseCircleOutlined style={{ marginRight: "8px", color: "#FA8015" }} />
  //   ),
  //   text: "停止",
  //   value: batchType.STOP
  // },
  // { ...splitLine },
  // {
  //   icon: (
  //     <CheckCircleOutlined style={{ marginRight: "8px", color: "#014DDF" }} />
  //   ),
  //   text: "启用",
  //   value: batchType.ENABLE,
  //   tabKey: "1"
  // },
  // {
  //   icon: <img src={IconDisabled} style={{ ...imgStyle }} />,
  //   text: "禁用",
  //   value: batchType.DISABLE,
  //   tabKey: "1"
  // },
  { ...splitLine, tabKey: tabItems[0].key, isCecShow: false },
  { ...splitLine, tabKey: tabItems[1].key, isCecShow: false },
  {
    text: "作为切片检索",
    value: batchType.SOURCE,
    tabKey: tabItems[0].key,
    isCecShow: true
  },
  {
    icon: <img src={IconDelete} style={{ ...imgStyle }} />,
    text: "批量删除",
    value: batchType.DELETE
  }
];
