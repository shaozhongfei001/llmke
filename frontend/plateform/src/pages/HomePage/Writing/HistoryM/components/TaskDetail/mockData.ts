export const mockTreeData = [
  {
    title: "一、授信方案",
    section: { id: 35762, hasSectionPrompt: false, hasContent: false },
    sectionId: 35762,
    contentOperation: "0",
    contentSources: [
      {
        sourceType: "database",
        refIds: ["131", "130"],
        refNames: ["company_info", "shareholder_info"],
        dbNames: ["customer", "customer"],
        refEntityType: "table"
      }
    ],
    useCustomDB: true,
    useCustomKb: false,
    subParagraphs: [
      {
        title: "（一）本次申报方案",
        section: { id: 35774, hasSectionPrompt: true, hasContent: false },
        sectionId: 35774,
        contentOperation: "0",
        contentSources: [
          {
            sourceType: "database",
            refIds: ["145", "144", "135", "134", "131", "130"],
            refNames: [
              "employees_tmp1",
              "employees_tmp",
              "shareholder_info",
              "company_info",
              "company_info",
              "shareholder_info"
            ],
            dbNames: [
              "customer",
              "customer",
              "customer",
              "customer",
              "customer",
              "customer"
            ],
            refEntityType: "table"
          }
        ],
        useCustomDB: true,
        useCustomKb: false
      },
      {
        title: "（一）企业基本信息",
        section: { id: 35775, hasSectionPrompt: true, hasContent: false },
        sectionId: 35775,
        contentOperation: "0",
        useCustomDB: false,
        useCustomKb: false
      },
      {
        title: "（二）本次申报方案说明",
        section: { id: 35776, hasSectionPrompt: true, hasContent: false },
        sectionId: 35776,
        contentOperation: "0",
        useCustomDB: false,
        useCustomKb: false
      },
      {
        title: "（三）借款人与我行银企合作情况",
        section: { id: 35777, hasSectionPrompt: true, hasContent: false },
        sectionId: 35777,
        contentOperation: "0",
        useCustomDB: false,
        useCustomKb: false
      },
      {
        title: "（四）借款人所在集团我行授信情况",
        section: { id: 35778, hasSectionPrompt: true, hasContent: false },
        sectionId: 35778,
        contentOperation: "0",
        useCustomDB: false,
        useCustomKb: false
      },
      {
        title: "（五）该笔贷款是否符合我行信贷政策",
        section: { id: 35779, hasSectionPrompt: true, hasContent: false },
        sectionId: 35779,
        contentOperation: "0",
        useCustomDB: false,
        useCustomKb: false
      }
    ]
  },
  {
    title: "二、借款人评价",
    section: { id: 35763, hasSectionPrompt: false, hasContent: false },
    sectionId: 35763,
    contentOperation: "0",
    contentSources: [
      {
        sourceType: "database",
        refIds: ["145", "144", "135", "134"],
        refNames: [
          "employees_tmp1",
          "employees_tmp",
          "shareholder_info",
          "company_info"
        ],
        dbNames: ["customer", "customer", "customer", "customer"],
        refEntityType: "table"
      }
    ],
    useCustomDB: true,
    useCustomKb: false,
    subParagraphs: [
      {
        title: "（二）关联方情况",
        section: { id: 35780, hasSectionPrompt: true, hasContent: false },
        sectionId: 35780,
        contentOperation: "0",
        useCustomDB: false,
        useCustomKb: false
      }
    ]
  },
  {
    title: "三、行业分析",
    section: { id: 35764, hasSectionPrompt: true, hasContent: false },
    sectionId: 35764,
    contentOperation: "0",
    useCustomDB: true,
    useCustomKb: false
  },
  {
    title: "四、经营分析",
    section: { id: 35765, hasSectionPrompt: false, hasContent: false },
    sectionId: 35765,
    contentOperation: "0",
    contentSources: [
      {
        sourceType: "database",
        refIds: [],
        refNames: [],
        dbNames: [],
        refEntityType: "table"
      }
    ],
    useCustomDB: true,
    useCustomKb: false,
    subParagraphs: [
      {
        title: "（一）生产经营介绍",
        section: { id: 35781, hasSectionPrompt: true, hasContent: false },
        sectionId: 35781,
        contentOperation: "0",
        contentSources: [],
        useCustomDB: false,
        useCustomKb: false
      },
      {
        title: "（二）其他经营相关情况",
        section: { id: 35782, hasSectionPrompt: true, hasContent: false },
        sectionId: 35782,
        contentOperation: "0",
        useCustomDB: false,
        useCustomKb: false
      }
    ]
  },
  {
    title: "五、财务分析",
    section: { id: 35766, hasSectionPrompt: false, hasContent: false },
    sectionId: 35766,
    contentOperation: "0",
    useCustomDB: true,
    useCustomKb: false,
    subParagraphs: [
      {
        title: "（一）报表情况",
        section: { id: 35783, hasSectionPrompt: true, hasContent: false },
        sectionId: 35783,
        contentOperation: "0",
        useCustomDB: false,
        useCustomKb: false
      },
      {
        title: "（二）财务报表",
        section: { id: 35784, hasSectionPrompt: true, hasContent: false },
        sectionId: 35784,
        contentOperation: "0",
        useCustomDB: false,
        useCustomKb: false
      },
      {
        title: "（三）财务评价",
        section: { id: 35785, hasSectionPrompt: true, hasContent: false },
        sectionId: 35785,
        contentOperation: "0",
        useCustomDB: false,
        useCustomKb: false
      },
      {
        title: "（四）短期偿债能力",
        section: { id: 35786, hasSectionPrompt: true, hasContent: false },
        sectionId: 35786,
        contentOperation: "0",
        useCustomDB: false,
        useCustomKb: false
      }
    ]
  },
  {
    title: "六、外部负债情况",
    section: { id: 35767, hasSectionPrompt: false, hasContent: false },
    sectionId: 35767,
    contentOperation: "0",
    useCustomDB: true,
    useCustomKb: false,
    subParagraphs: [
      {
        title: "（一）银行征信查询",
        section: { id: 35787, hasSectionPrompt: true, hasContent: false },
        sectionId: 35787,
        contentOperation: "0",
        useCustomDB: false,
        useCustomKb: false
      },
      {
        title: "（二）借款人全部有息负债情况",
        section: { id: 35788, hasSectionPrompt: true, hasContent: false },
        sectionId: 35788,
        contentOperation: "0",
        useCustomDB: false,
        useCustomKb: false
      },
      {
        title: "（三）对外担保情况",
        section: { id: 35789, hasSectionPrompt: true, hasContent: false },
        sectionId: 35789,
        contentOperation: "0",
        useCustomDB: false,
        useCustomKb: false
      },
      {
        title: "（四）银企合作情况",
        section: { id: 35790, hasSectionPrompt: true, hasContent: false },
        sectionId: 35790,
        contentOperation: "0",
        useCustomDB: false,
        useCustomKb: false
      }
    ]
  },
  {
    title: "七、外部不良信息",
    section: { id: 35768, hasSectionPrompt: false, hasContent: false },
    sectionId: 35768,
    contentOperation: "0",
    contentSources: [
      {
        sourceType: "database",
        refIds: [],
        refNames: [],
        dbNames: [],
        refEntityType: "table"
      }
    ],
    useCustomDB: true,
    useCustomKb: false,
    subParagraphs: [
      {
        title:
          "（一）借款人及关联方是否存在逾期、欠息等不良信息，以及是否存在账户查封、被纳入失信被执行人等信息。",
        section: { id: 35791, hasSectionPrompt: false, hasContent: false },
        sectionId: 35791,
        contentOperation: "0",
        useCustomDB: false,
        useCustomKb: false
      },
      {
        title:
          "（二）借款人及关联方是否已卷入或即将卷入重大的诉讼或仲裁程序及其他法律纠纷等。",
        section: { id: 35792, hasSectionPrompt: false, hasContent: false },
        sectionId: 35792,
        contentOperation: "0",
        useCustomDB: false,
        useCustomKb: false
      },
      {
        title: "（三）借款人及关联方是否存在外部重大负面舆论信息。",
        section: { id: 35793, hasSectionPrompt: false, hasContent: false },
        sectionId: 35793,
        contentOperation: "0",
        useCustomDB: false,
        useCustomKb: false
      }
    ]
  },
  {
    title: "八、担保方案",
    section: { id: 35769, hasSectionPrompt: false, hasContent: false },
    sectionId: 35769,
    contentOperation: "0",
    useCustomDB: true,
    useCustomKb: false,
    subParagraphs: [
      {
        title: "（一）担保方案介绍",
        section: { id: 35794, hasSectionPrompt: true, hasContent: false },
        sectionId: 35794,
        contentOperation: "0",
        useCustomDB: false,
        useCustomKb: false,
        subParagraphs: [
          {
            title: "反反复复",
            section: { id: 35800, hasSectionPrompt: true, hasContent: false },
            sectionId: 35800,
            contentOperation: "0",
            useCustomDB: false,
            useCustomKb: false
          }
        ]
      },
      {
        title: "（二）担保人/抵质押物分析",
        section: { id: 35795, hasSectionPrompt: true, hasContent: false },
        sectionId: 35795,
        contentOperation: "0",
        useCustomDB: false,
        useCustomKb: false
      },
      {
        title: "（三）担保能力评价",
        section: { id: 35796, hasSectionPrompt: true, hasContent: false },
        sectionId: 35796,
        contentOperation: "0",
        useCustomDB: false,
        useCustomKb: false
      }
    ]
  },
  {
    title: "九、贷款合理性分析",
    section: { id: 35770, hasSectionPrompt: false, hasContent: false },
    sectionId: 35770,
    contentOperation: "0",
    contentSources: [
      {
        sourceType: "database",
        refIds: ["135", "134"],
        refNames: ["shareholder_info", "company_info"],
        dbNames: ["customer", "customer"],
        refEntityType: "table"
      }
    ],
    useCustomDB: true,
    useCustomKb: false,
    subParagraphs: [
      {
        title: "（一）流动资金需求测算",
        section: { id: 35797, hasSectionPrompt: true, hasContent: false },
        sectionId: 35797,
        contentOperation: "0",
        contentSources: [],
        useCustomDB: false,
        useCustomKb: false
      },
      {
        title: "（二）贷款额度合理性分析",
        section: { id: 35798, hasSectionPrompt: true, hasContent: false },
        sectionId: 35798,
        contentOperation: "0",
        useCustomDB: false,
        useCustomKb: false
      },
      {
        title: "（三）贷款还款能力评价",
        section: { id: 35799, hasSectionPrompt: true, hasContent: false },
        sectionId: 35799,
        contentOperation: "0",
        useCustomDB: false,
        useCustomKb: false
      }
    ]
  },
  {
    title: "十、本笔贷款法律问题",
    section: { id: 35771, hasSectionPrompt: true, hasContent: false },
    sectionId: 35771,
    contentOperation: "0",
    useCustomDB: true,
    useCustomKb: false
  },
  {
    title: "十一、风险提示与防范措施",
    section: { id: 35772, hasSectionPrompt: true, hasContent: false },
    sectionId: 35772,
    contentOperation: "0",
    useCustomDB: true,
    useCustomKb: false
  },
  {
    title: "十二、分支机构意见",
    section: { id: 35773, hasSectionPrompt: true, hasContent: false },
    sectionId: 35773,
    contentOperation: "0",
    contentSources: [
      {
        sourceType: "database",
        refIds: [],
        refNames: [],
        dbNames: [],
        refEntityType: "table"
      }
    ],
    useCustomDB: true,
    useCustomKb: false
  }
];

export const taskTimeList = [
  {
    label: "2025-03-25 09:21",
    value: 4
  },
  {
    label: "2025-03-21 10:00",
    value: 5
  },
  {
    label: "2025-03-19 16:28",
    value: 6
  },
  {
    label: "2025-03-15 08:12",
    value: 7
  }
];
