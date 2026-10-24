const getArticleTypeDetails_mockData = {
  success: true,
  // data: {
  //   id: 43,
  //   gmtCreate: '2024-08-15 02:06:14',
  //   gmtModified: '2024-08-23 17:09:22',
  //   name: '邮件',
  //   promptTemplateUser: '请写一封邮件 发送对象是{A}，邮件内容是{B}，时间是{C}，发出人是{D}',
  //   formatTemplate:
  //     '{"htmlSchema":"<h1 id=\\"redtitle\\">{发文机关}文件</h1><h5>{发文字号}</h5><hr class=\\"red-line\\"></hr><p></p ><h2>{请示标题}</h2><h3>{主送机关}：</h3><p>[content]</p ><h4>{发文机关}</h4><h4>{发文时间}</h4><h3>（联系人：{联系人}   联系方式：{联系方式}）</h3>","cssSchema":"{\\"heading\\":{\\"h1\\":{\\"fontSize\\":\\"45pt\\",\\"lineHeight\\":\\"1.5\\",\\"color\\":\\"red\\",\\"fontFamily\\":\\"宋体\\",\\"textAlign\\":\\"center\\"},\\"h2\\":{\\"fontSize\\":\\"40px\\",\\"lineHeight\\":\\"1.5\\",\\"fontFamily\\":\\"宋体\\",\\"textAlign\\":\\"center\\"},\\"h3\\":{\\"fontSize\\":\\"16px\\",\\"lineHeight\\":\\"1.5\\",\\"fontFamily\\":\\"仿宋\\",\\"textAlign\\":\\"left\\",\\"fontWeight\\":\\"normal\\"},\\"h4\\":{\\"fontSize\\":\\"16px\\",\\"lineHeight\\":\\"1.5\\",\\"fontFamily\\":\\"仿宋\\",\\"textAlign\\":\\"right\\",\\"fontWeight\\":\\"normal\\"},\\"h5\\":{\\"fontSize\\":\\"14px\\",\\"lineHeight\\":\\"22px\\",\\"fontFamily\\":\\"仿宋\\",\\"fontWeight\\":\\"normal\\",\\"textAlign\\":\\"center\\"}},\\"p\\":{\\"fontSize\\":\\"16px\\",\\"lineHeight\\":\\"1.8\\",\\"color\\":\\"#222\\",\\"fontFamily\\":\\"仿宋\\",\\"textIndent\\":\\"2em\\"}}"}',
  //   // formatTemplate:
  //   //   '{"htmlSchema":"<h1 id=\\"redtitle\\">{发文机关}文件</h1><h5>{发文字号}</h5><hr class=\\"red-line\\"></hr><p></p><h2>{请示标题}</h2><h3>{主送机关}：</h3><p>[content]</p><h4>{发文机关}</h4><h4>{发文时间}</h4><h3>（联系人：{联系人}   联系方式：{联系方式}）</h3>","cssSchema":"{\\"heading\\":{\\"h1\\":{\\"fontSize\\":\\"45pt\\",\\"lineHeight\\":\\"1.5\\",\\"color\\":\\"red\\",\\"fontFamily\\":\\"宋体\\",\\"textAlign\\":\\"center\\"},\\"h2\\":{\\"fontSize\\":\\"40px\\",\\"lineHeight\\":\\"1.5\\",\\"fontFamily\\":\\"宋体\\",\\"textAlign\\":\\"center\\"},\\"h3\\":{\\"fontSize\\":\\"16px\\",\\"lineHeight\\":\\"1.5\\",\\"fontFamily\\":\\"仿宋\\",\\"textAlign\\":\\"left\\",\\"fontWeight\\":\\"normal\\"},\\"h4\\":{\\"fontSize\\":\\"16px\\",\\"lineHeight\\":\\"1.5\\",\\"fontFamily\\":\\"仿宋\\",\\"textAlign\\":\\"right\\",\\"fontWeight\\":\\"normal\\"},\\"h5\\":{\\"fontSize\\":\\"14px\\",\\"lineHeight\\":\\"22px\\",\\"fontFamily\\":\\"仿宋\\",\\"fontWeight\\":\\"normal\\",\\"textAlign\\":\\"center\\"}},\\"p\\":{\\"fontSize\\":\\"16px\\",\\"lineHeight\\":\\"1.8\\",\\"color\\":\\"#222\\",\\"fontFamily\\":\\"仿宋\\",\\"textIndent\\":\\"2em\\"}}"}',
  //   // formatTemplate: {
  //   //   htmlSchema:
  //   //     '<h1 id="redtitle">{发文机关}文件</h1><h5>{发文字号}</h5><hr class="red-line"></hr><p></p><h2>{请示标题}</h2><h3>{主送机关}：</h3><p>[content]</p><h4>{发文机关}</h4><h4>{发文时间}</h4><h3>（联系人：{联系人}   联系方式：{联系方式}）</h3>',
  //   //   cssSchema:
  //   //     '{"heading":{"h1":{"fontSize":"45pt","lineHeight":"1.5","color":"red","fontFamily":"宋体","textAlign":"center"},"h2":{"fontSize":"40px","lineHeight":"1.5","fontFamily":"宋体","textAlign":"center"},"h3":{"fontSize":"16px","lineHeight":"1.5","fontFamily":"仿宋","textAlign":"left","fontWeight":"normal"},"h4":{"fontSize":"16px","lineHeight":"1.5","fontFamily":"仿宋","textAlign":"right","fontWeight":"normal"},"h5":{"fontSize":"14px","lineHeight":"22px","fontFamily":"仿宋","fontWeight":"normal","textAlign":"center"}},"p":{"fontSize":"16px","lineHeight":"1.8","color":"#222","fontFamily":"仿宋","textIndent":"2em"}}',
  //   // },
  //   paramsSchema:
  //     '{"uiSchema":[{"key":1,"dataIndex":"title","title":"文章标题","required":true,"type":"string"},{"key":"02e8a0dcf84","dataIndex":"a","title":"发文机关","required":true,"type":"string"},{"key":"2e8a0dcf84d","dataIndex":"b","title":"发文字号","required":true,"type":"string"},{"key":"e8a0dcf84d7","dataIndex":"c","title":"请示标题","required":true,"type":"string"},{"key":"8a0dcf84d73","dataIndex":"d","title":"请示内容","required":true,"type":"string"},{"key":"a0dcf84d737","dataIndex":"e","title":"请示缘由","required":false,"type":"string"},{"key":"0dcf84d7378","dataIndex":"f","title":"结语","required":false,"type":"string"},{"key":"dcf84d73789","dataIndex":"g","title":"联系人","required":true,"type":"string"},{"key":"cf84d737896","dataIndex":"h","title":"联系方式","required":true,"type":"string"},{"key":"f84d7378964","dataIndex":"i","title":"主送机关","required":true,"type":"string"},{"key":"84d73789642","dataIndex":"j","title":"发文时间","required":true,"type":"string"}],"$id":"75534d3106a","title":"请示【红头文件】","properties":{},"required":[],"description":"","type":""}',
  //   versionId: 95,
  // },
  data: {
    success: true,
    errorMsg: "",
    errorCode: "0",
    data: {
      id: -3,
      gmtCreate: "2024-11-22 13:47:17",
      gmtModified: "2024-11-29 11:10:08",
      name: "通用文稿",
      promptTemplateSystem: "*****",
      promptTemplateUser:
        "* 文章标题：{{title}}\n* 内容描述：{{contentAbstract}}\n* 语言风格：{{languageStyle}}\n* 字数要求：{{lengthLimit}}",
      paramsSchema:
        '{"uiSchema":[{"key":1,"dataIndex":"title","title":"文章标题","required":true,"type":"string"},{"key":"cf98043596a","dataIndex":"contentAbstract","title":"内容描述","required":true,"type":"longString"},{"key":"1dcdea3e8c4","dataIndex":"languageStyle","title":"语言风格","required":false,"type":"select","defaultValue":["正式严谨","温和礼貌","生动活泼","简洁干练","热情洋溢","口语化","辞藻华丽"]},{"key":"3cf98043596","dataIndex":"lengthLimit","title":"字数要求","required":false,"type":"string"}],"$id":"cdea3e8c48c","title":"通用文稿","properties":{},"required":[],"description":"","type":""}',
      versionId: 280,
      supportMaterials: 1,
      traceToMaterial: 1,
      contentRule: "",
      supportOutlines: 1,
      className: "其他",
      articleTypeKey: "normal",
      hasFormatTemplate: false,
      outputFormat: 0,
    },
  },
};

export { getArticleTypeDetails_mockData };

// formatTemplate: {
//   htmlSchema:'<h1 id="redtitle">{发文机关}文件</h1><h5>{发文字号}</h5><hr class="red-line"></hr><p></p><h2>{意见标题}</h2><h3>{主送机关}：</h3><p>[content]</p><h4>{发文机关}</h4><h4>{发文时间}</h4>',
//   cssSchema:
//     '{"heading":{"h1":{"fontSize":"45pt","lineHeight":"1.5","color":"red","fontFamily":"宋体","textAlign":"center"},"h2":{"fontSize":"40px","lineHeight":"1.5","fontFamily":"宋体","textAlign":"center"},"h3":{"fontSize":"16px","lineHeight":"1.5","fontFamily":"仿宋","textAlign":"left","fontWeight":"normal"},"h4":{"fontSize":"16px","lineHeight":"1.5","fontFamily":"仿宋","textAlign":"right","fontWeight":"normal"},"h5":{"fontSize":"14px","lineHeight":"22px","fontFamily":"仿宋","fontWeight":"normal","textAlign":"center"}},"p":{"fontSize":"16px","lineHeight":"1.8","color":"#222","fontFamily":"仿宋","textIndent":"2em"}}',
// },

// formatTemplate: {
//   htmlSchema:'<h1 id="redtitle">{发文机关}文件</h1><h5>{发文字号}</h5><hr class="red-line"></hr><p></p><h2>{报告标题}</h2><h3>{主送机关}：</h3><p>[content]</p><h4>{发文机关}</h4><h4>{发文时间}</h4>',
//   cssSchema:
//     '{"heading":{"h1":{"fontSize":"45pt","lineHeight":"1.5","color":"red","fontFamily":"宋体","textAlign":"center"},"h2":{"fontSize":"40px","lineHeight":"1.5","fontFamily":"宋体","textAlign":"center"},"h3":{"fontSize":"16px","lineHeight":"1.5","fontFamily":"仿宋","textAlign":"left","fontWeight":"normal"},"h4":{"fontSize":"16px","lineHeight":"1.5","fontFamily":"仿宋","textAlign":"right","fontWeight":"normal"},"h5":{"fontSize":"14px","lineHeight":"22px","fontFamily":"仿宋","fontWeight":"normal","textAlign":"center"}},"p":{"fontSize":"16px","lineHeight":"1.8","color":"#222","fontFamily":"仿宋","textIndent":"2em"}}',
// },
