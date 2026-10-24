import xls from "@/assets/writing/xls.png";
import doc from "@/assets/writing/doc.png";
import pdf from "@/assets/writing/pdf.png";
import ppt from "@/assets/writing/ppt.png";
export const tabItems = [
  {
    key: "commonLib",
    label: "我的上传"
  },
  {
    key: "demoLib",
    label: "范文库"
  },
  {
    key: "lawLib",
    label: "法规库"
  }
];
export const sceneTagMap = [
  {
    key: "all",
    label: "全部"
  },
  {
    key: "bank",
    label: "银行"
  },
  {
    key: "insurance",
    label: "保险"
  },
  {
    key: "security",
    label: "证券"
  },
  {
    key: "other",
    label: "其他"
  }
];
export const styleTagMap = [
  {
    key: "all",
    label: "全部"
  },
  {
    key: "notice",
    label: "通知公告"
  },
  {
    key: "report",
    label: "工作报告"
  },
  {
    key: "survey",
    label: "调研报告"
  },
  {
    key: "invitation",
    label: "邀请函"
  },
  {
    key: "understanding",
    label: "心得体会"
  },
  {
    key: "speech",
    label: "讲话稿"
  },
  {
    key: "other",
    label: "其他"
  }
];

export const modalStyles = {
  header: {
    padding: "20px 24px",
    borderBottom: "1px solid #F0F0F0",
    margin: 0
  },
  body: { padding: 0 },
  mask: {},
  footer: { padding: 0, margin: 0 },
  content: { padding: 0 }
};

export const FILEIMG: any = {
  docx: doc,
  doc: doc,
  pdf: pdf,
  xls: xls,
  xlsx: xls,
  ppt: ppt,
  pptx: ppt,
  pub: ppt
};
