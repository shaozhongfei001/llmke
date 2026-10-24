const templateMock = {
  id: 32,
  gmtCreate: "2024-12-04 19:50:42",
  gmtModified: "2024-12-05 07:14:17",
  name: "尽调报告模板【百度·资产智评】",
  promptTemplateUser: "分段生成无需配置",
  paramsSchema:
    '{"uiSchema":[{"key":1,"dataIndex":"title","title":"文章标题","required":true,"type":"string"},{"key":"f7cf1fb489c","dataIndex":"applicant","title":"申请人","required":true,"type":"string"},{"key":"7cf1fb489c8","dataIndex":"declarationBank","title":"申报行","required":true,"type":"string"},{"key":"cf1fb489c89","dataIndex":"investigator","title":"调查人员","required":true,"type":"string"},{"key":"fb489c8901d","dataIndex":"time","title":"填报时间","required":true,"type":"date"}],"$id":"89c8901dc9b","title":"尽调报告模板【百度·资产智评】","properties":{},"required":[],"description":"","type":""}',
  versionId: 262,
  supportMaterials: 1,
  traceToMaterial: 0,
  contentRule: "",
  supportOutlines: 0,
  className: "尽调",
  articleTypeKey: "",
  hasFormatTemplate: false,
  outputFormat: 1,
  stateProcess: '["场景基本信息", "大纲及素材"]',
  state: 1,
  generateType: 1,
  outlines: {
    paragraphs: [
      {
        title: "一、企业基本信息",
        subParagraphs: [
          {
            title: "1.1. 工商信息",
            sectionId: 1,
            section: { materialType: [6] },
            contentSources: [
              {
                sourceType: "materials",
                refIds: [109],
                refNames: [
                  "关于印发《杭州银行预期信用损失法实施管理办法》的通知.pdf"
                ],
                materialTypeIds: [6]
              }
            ],
            contentOperation: "1"
          },
          {
            title: "1.2. 主要股东情况",
            sectionId: 2,
            section: { materialType: [3] },
            contentSources: [
              {
                sourceType: "materials",
                refIds: [201, 200],
                refNames: [
                  "放假通知.doc",
                  "关于进一步规范集团公司公文处理工作的通知.pdf"
                ],
                materialTypeIds: [3, 3]
              }
            ],
            contentOperation: "1"
          }
        ]
      },
      {
        title: "二、行业分析",
        subParagraphs: [
          {
            title: "2.1. 行业概况及竞争",
            sectionId: 3,
            section: { materialType: [3, 4] }
          },
          {
            title: "2.2. 公司主要业务与技术",
            sectionId: 4,
            section: { materialType: [3, 4] }
          }
        ]
      },
      {
        title: "三、公司经营与财务分析",
        subParagraphs: [
          {
            title: "3.1. 主营业务及成本分析",
            subParagraphs: [
              {
                title: "3.1.1. 资产负债表",
                sectionId: 9,
                section: { materialType: [6, 7, 3, 4] },
                contentSources: [
                  {
                    sourceType: "materials",
                    refIds: [109, 109, 201, 200],
                    refNames: [
                      "关于印发《杭州银行预期信用损失法实施管理办法》的通知.pdf",
                      "关于印发《杭州银行预期信用损失法实施管理办法》的通知.pdf",
                      "放假通知.doc",
                      "关于进一步规范集团公司公文处理工作的通知.pdf"
                    ],
                    materialTypeIds: [6, 7, 3, 4]
                  }
                ]
              },
              {
                title: "3.1.2. 利润表",
                sectionId: 10,
                section: { materialType: [4] }
              }
            ]
          },
          {
            title: "3.2. 偿债能力分析",
            sectionId: 5,
            section: { materialType: [4] }
          },
          {
            title: "3.3. 现金流量分析",
            sectionId: 6,
            section: { materialType: [4] }
          }
        ]
      },
      {
        title: "四、上下游主要客户",
        sectionId: 7,
        section: { materialType: [] }
      },
      {
        title: "五、潜在风险分析",
        sectionId: 8,
        section: { materialType: [] }
      }
    ]
  }
};

export const docMock = {
  id: 680,
  gmtCreate: "2024-12-07 14:28:52",
  gmtModified: "2024-12-07 14:28:52",
  status: 1,
  userId: "1000",
  title: "生成对公固定资产尽调报告",
  contentSources: [],
  articleType: 0,
  articleSubType: 0,
  extraParams: {
    investigator: "zj",
    time: "2024-12-07",
    title: "生成对公固定资产尽调报告",
    declarationBank: "中国银行",
    applicant: "赵婧"
  },
  articleTypeId: 0,
  articleTypeVersionId: 0,
  lastHintVersionId: 0,
  outputFormat: 0,
  outlines: {
    coverPage: {
      sectionId: 1682
    },
    paragraphs: [
      {
        title: "一、企业基本信息",
        subParagraphs: [
          {
            title: "1.1. 工商信息",
            // contentSources: [],
            subParagraphs: [],
            sectionId: 1674,
            section: {
              id: 1674
              // materialType: [3]
            }
          }
        ]
      }
    ]
  }
};

const uploadMaterialList = [
  {
    id: 201,
    fileName: "放假通知.doc",
    fileUrl:
      "http://10.64.7.145:9000/dev-brain-data/commonLib/1000/放假通知.doc",
    state: 2,
    material_type: [3, 4]
  },
  {
    id: 200,
    fileName: "关于进一步规范集团公司公文处理工作的通知.pdf",
    fileUrl:
      "http://10.64.7.145:9000/dev-brain-data/commonLib/1000/关于进一步规范集团公司公文处理工作的通知.pdf",
    state: 3,
    material_type: [3]
  },
  {
    id: 109,
    fileName: "关于印发《杭州银行预期信用损失法实施管理办法》的通知.pdf",
    fileUrl:
      "http://10.15.12.12:9000/dev-brain-data/1000/关于印发《杭州银行预期信用损失法实施管理办法》的通知.pdf",
    state: 4,
    material_type: [6, 7]
  }
];

const newL = [
  {
    id: 109,
    fileName: "关于印发《杭州银行预期信用损失法实施管理办法》的通知.pdf",
    fileUrl:
      "http://10.15.12.12:9000/dev-brain-data/1000/关于印发《杭州银行预期信用损失法实施管理办法》的通知.pdf",
    state: 3,
    material_type: [6, 7]
  }
];
