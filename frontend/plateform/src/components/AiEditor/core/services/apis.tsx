import {
  articleFeedback_mockData,
  exportArticleById_mockData,
  generateOutline_mockData,
  getArticleMaterialList_mockData,
  getArticleTypeDetails_mockData,
  getArticleTypeList_mockData,
  getFileContent_mockData,
  getParseTextByUploadFile_mockData,
  markSensitiveWord_mockData,
  queryArticleDetail_mockData,
  review_mockData,
  reviewArticleByContentRule_mockData,
  saveArticleContent_mockData,
  saveArticleSetting_mockData
} from "../mocks";

export const apis = {
  getArticleById: {
    url: "/dw/article/queryArticleDetail",
    method: "get",
    mockData: queryArticleDetail_mockData
  },
  review: {
    url: "/dw/article/review",
    method: "post",
    mockData: review_mockData
  },
  generateOutline: {
    url: "/dw/article/generateOutlines",
    method: "post",
    mockData: generateOutline_mockData
  },
  getArticleTypeList: {
    url: "/dw/articleType",
    method: "get",
    mockData: getArticleTypeList_mockData
  },
  getArticleTypeDetails: {
    url: "/dw/articleType",
    method: "get",
    mockData: getArticleTypeDetails_mockData
  },
  saveArticleSetting: {
    url: "/dw/article/saveArticleSettings",
    method: "post",
    mockData: saveArticleSetting_mockData
  },
  putDependencyDetect: {
    url: "/dw/articleTask/dependency/detect",
    method: "put",
    mockData: {}
  },
  saveArticleContent: {
    url: "/dw/article/saveArticleContent",
    method: "post",
    mockData: saveArticleContent_mockData
  },
  getArticleMaterialList: {
    url: "/dw/articleMaterial",
    method: "get",
    mockData: getArticleMaterialList_mockData
  },
  markSensitiveWord: {
    url: `/dw/article`,
    method: "get",
    mockData: markSensitiveWord_mockData
  },
  // 根据内容规范审核文章（生成文章后立即调用）
  reviewArticleByContentRule: {
    url: `/dw/article/reviewArticleByContentRule`,
    method: "post",
    mockData: reviewArticleByContentRule_mockData
  },
  // 下载
  exportArticleById: {
    url: `/dw/article/export`,
    method: "get",
    mockData: exportArticleById_mockData
  },
  // 反馈
  articleFeedback: {
    url: `/dw/articleFeedback/report`,
    method: "post",
    mockData: articleFeedback_mockData
  },
  // 上传文件返回html，用于上传文件写作
  getParseTextByUploadFile: {
    url: "/dw/articleMaterial/parseText",
    method: "post",
    mockData: getParseTextByUploadFile_mockData
  },
  // 根据url获取文件内容
  getFileContent: {
    method: "get",
    mockData: getFileContent_mockData
  },
  // 根据id获取文件解析状态
  getFileStatusByIds: {
    url: "/dw/articleMaterial",
    method: "get",
    mockData: {}
  },
  getSectionById: {
    url: "/dw/article/section",
    method: "get",
    mockData: {}
  },
  getSectionByVersionId: {
    url: "/dw/articleType",
    method: "get",
    mockData: {}
  },
  editSectionById: {
    url: "/dw/article",
    method: "put",
    mockData: {}
  },
  addSection: {
    url: "/dw/article",
    method: "post",
    mockData: {}
  },
  editArticleTypeSectionById: {
    url: "/dw/articleType",
    method: "put",
    mockData: {}
  },
  addArticleTypeSection: {
    url: "/dw/articleType",
    method: "post",
    mockData: {}
  },
  applyOutlines: {
    url: "/dw/articleType",
    method: "post",
    mockData: {}
  },
  applySection: {
    url: "/dw/component/section",
    method: "post",
    mockData: {}
  },
  deleteSections: {
    url: "/dw",
    method: "delete",
    mockData: {}
  },
  retryParseMaterial: {
    url: "/dw/articleMaterial/parse",
    method: "post",
    mockData: {}
  },
  getMaterialType: {
    url: "/dw/materialType",
    method: "get",
    mockData: {}
  },
  putArticleMaterialList: {
    url: "/dw/articleMaterial",
    method: "put",
    mockData: {}
  },
  getDataBase: {
    url: "/dw/index/matchQuery",
    method: "post",
    mockData: {}
  },
  // 批量保存content
  batchSave: {
    url: "/section/batchSave",
    method: "put",
    mockData: {}
  },
  // 生成图表(股权结构图)
  completeChart: {
    url: "",
    method: "post",
    mockData: {
      success: true,
      errorMsg: "",
      errorCode: "0",
      data: {
        chart:
          "flowchart RL\n    subgraph 二级股东\n    SH1_1[戴茂州 (53.35%)]\n    SH1_2[高巍 (20%)]\n    SH1_3[廖运健 (15%)]\n    SH1_4[顾航 (2.30%)]\n    SH1_5[李娜娜 (2.10%)]\n    SH1_6[成都泽厦企业管理中心 (2%)]\n    SH1_7[齐玉婷 (1.60%)]\n    SH1_8[杨小兵 (1.06%)]\n    SH1_9[夏红健 (1%)]\n    SH1_10[王卓 (1%)]\n    SH2_1[周任重]\n    SH2_2[商建洲]\n    SH2_3[四川国经创新投资管理有限公司]\n    SH2_4[山东省高新技术创业投资有限公司]\n    SH3_1[严建亚 (33.98%)]\n    SH3_2[西安市创新投资基金合伙企业 (22.40%)]\n    SH3_3[陕西省政府投资引导基金合伙企业 (22.40%)]\n    SH3_4[何建祥 (2.24%)]\n    SH3_5[袁群利 (2.24%)]\n    end\n\n    subgraph 一级股东\n    SH1[成都诺晶企业管理中心 (45.63%)]\n    SH2[成都鲁信菁蓉创业投资中心 (13.21%)]\n    SH3[陕西三元航科投资基金合伙企业 (9.49%)]\n    SH4[成都航远创科企业管理中心 (7.95%)]\n    SH5[亚洲新能源微电子咨询管理有限公司 (7.60%)]\n    SH6[聊城睿高致远股权投资合伙企业 (4.53%)]\n    SH7[温州市青峰创业投资合伙企业 (3.46%)]\n    SH8[成都矽能科技有限公司 (2.17%)]\n    SH9[成都诺友企业管理中心 (1.59%)]\n    SH10[南京泰华股权投资管理中心 (1.49%)]\n    end\n\n    subgraph 目标公司\n    MAIN[成都蓉矽半导体有限公司]\n    end\n\n    SH1_1 -->|持股53.35%| SH1\n    SH1_2 -->|持股20%| SH1\n    SH1_3 -->|持股15%| SH1\n    SH1_4 -->|持股2.30%| SH1\n    SH1_5 -->|持股2.10%| SH1\n    SH1_6 -->|持股2%| SH1\n    SH1_7 -->|持股1.60%| SH1\n    SH1_8 -->|持股1.06%| SH1\n    SH1_9 -->|持股1%| SH1\n    SH1_10 -->|持股1%| SH1\n    SH2_1 -->|持股| SH2\n    SH2_2 -->|持股| SH2\n    SH2_3 -->|持股| SH2\n    SH2_4 -->|持股| SH2\n    SH3_1 -->|持股33.98%| SH3\n    SH3_2 -->|持股22.40%| SH3\n    SH3_3 -->|持股22.40%| SH3\n    SH3_4 -->|持股2.24%| SH3\n    SH3_5 -->|持股2.24%| SH3\n    SH1 -->|持股45.63%| MAIN\n    SH2 -->|持股13.21%| MAIN\n    SH3 -->|持股9.49%| MAIN\n    SH4 -->|持股7.95%| MAIN\n    SH5 -->|持股7.60%| MAIN\n    SH6 -->|持股4.53%| MAIN\n    SH7 -->|持股3.46%| MAIN\n    SH8 -->|持股2.17%| MAIN\n    SH9 -->|持股1.59%| MAIN\n    SH10 -->|持股1.49%| MAIN\n\n    style MAIN fill:#f9f,stroke:#333,stroke-width:4px,font-size:18px\n    style SH1 fill:#bbf,stroke:#333,font-size:16px\n    style SH2 fill:#bbf,stroke:#333,font-size:16px\n    style SH3 fill:#bbf,stroke:#333,font-size:16px\n    style SH4 fill:#bbf,stroke:#333,font-size:16px\n    style SH5 fill:#bbf,stroke:#333,font-size:16px\n    style SH6 fill:#bbf,stroke:#333,font-size:16px\n    style SH7 fill:#bbf,stroke:#333,font-size:16px\n    style SH8 fill:#bbf,stroke:#333,font-size:16px\n    style SH9 fill:#bbf,stroke:#333,font-size:16px\n    style SH10 fill:#bbf,stroke:#333,font-size:16px\n    style SH1_1 fill:#ddf,stroke:#333,font-size:14px\n    style SH1_2 fill:#ddf,stroke:#333,font-size:14px\n    style SH1_3 fill:#ddf,stroke:#333,font-size:14px\n    style SH1_4 fill:#ddf,stroke:#333,font-size:14px\n    style SH1_5 fill:#ddf,stroke:#333,font-size:14px\n    style SH1_6 fill:#ddf,stroke:#333,font-size:14px\n    style SH1_7 fill:#ddf,stroke:#333,font-size:14px\n    style SH1_8 fill:#ddf,stroke:#333,font-size:14px\n    style SH1_9 fill:#ddf,stroke:#333,font-size:14px\n    style SH1_10 fill:#ddf,stroke:#333,font-size:14px\n    style SH2_1 fill:#ddf,stroke:#333,font-size:14px\n    style SH2_2 fill:#ddf,stroke:#333,font-size:14px\n    style SH2_3 fill:#ddf,stroke:#333,font-size:14px\n    style SH2_4 fill:#ddf,stroke:#333,font-size:14px\n    style SH3_1 fill:#ddf,stroke:#333,font-size:14px\n    style SH3_2 fill:#ddf,stroke:#333,font-size:14px\n    style SH3_3 fill:#ddf,stroke:#333,font-size:14px\n    style SH3_4 fill:#ddf,stroke:#333,font-size:14px\n    style SH3_5 fill:#ddf,stroke:#333,font-size:14px"
      }
    }
  },
  // 上传图片
  storeFiles: {
    url: "/dw/articleMaterial/storeFiles",
    method: "post",
    mockData: {}
  },
  addArticleTask: {
    url: "/dw/articleTask",
    method: "post",
    mockData: {}
  }
};
