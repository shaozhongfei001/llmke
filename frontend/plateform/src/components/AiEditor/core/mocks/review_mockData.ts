const review_mockData = {
  success: true,
  errorMsg: '',
  errorCode: '0',
  data: [
    {
      id: 1,
      errorType: 8,
      errorContent: '在次过程中',
      targetContent: '在此过程中',
      tips: '“在次过程中”中的“次”应为“此”',
      errorContext: {
        errorContent: '元化需求。在次过程中，我们不仅',
        targetContent: '元化需求。在此过程中，我们不仅',
      },
    },
    {
      id: 2,
      errorType: 1,
      errorContent: '实线了自身的稳健发展',
      targetContent: '实现了自身的稳健发展',
      tips: '“实线了”中的“线”应为“现”',
      errorContext: {
        errorContent: '，我们不仅实线了自身的稳健发展，也为促进',
        targetContent: '，我们不仅实现了自身的稳健发展，也为促进',
      },
    },
    {
      id: 3,
      errorType: 5,
      errorContent:
        '加快发展速度与业务规模 这家公司目前已经成为拥有4大板块、11个厂家，稳居行业第二，为了防止安全事故不再发生，项目失败的原因是由于需求失控。',
      targetContent:
        '加快发展速度与业务规模，本行目前已经成为拥有4大板块、11个厂家，稳居行业第二。为了防止安全事故不再发生，项目失败的原因是由于需求失控。',
      tips: '缺少“本行”一词，且缺少逗号分隔句子',
      errorContext: {
        errorContent:
          '积极贡献。加快发展速度与业务规模 这家公司目前已经成为拥有4大板块、11个厂家，稳居行业第二，为了防止安全事故不再发生，项目失败的原因是由于需求失控。本行深知作',
        targetContent:
          '积极贡献。加快发展速度与业务规模，本行目前已经成为拥有4大板块、11个厂家，稳居行业第二。为了防止安全事故不再发生，项目失败的原因是由于需求失控。本行深知作',
      },
    },
    {
      id: 4,
      errorType: 4,
      errorContent: '本行深知作为一家负责任金融机构的南华早报重要性',
      targetContent: '本行深知作为一家负责任金融机构的重要性',
      tips: '“南华早报”为冗余信息',
      errorContext: {
        errorContent: '需求失控。本行深知作为一家负责任金融机构的南华早报重要性，因此，在',
        targetContent: '需求失控。本行深知作为一家负责任金融机构的重要性，因此，在',
      },
    },
    {
      id: 5,
      errorType: 5,
      errorContent: '企业的成功离不开对的贡献和支持',
      targetContent: '企业的成功离不开社会的贡献和支持',
      tips: '缺少“社会”一词',
      errorContext: {
        errorContent: '我们坚信，企业的成功离不开对的贡献和支持。浙商银行',
        targetContent: '我们坚信，企业的成功离不开社会的贡献和支持。浙商银行',
      },
    },
    {
      id: 6,
      errorType: 4,
      errorContent: '浙商银行的核心价值观在于诚信、卡斯特罗创新以及客户至上',
      targetContent: '浙商银行的核心价值观在于诚信、创新以及客户至上',
      tips: '“卡斯特罗”为冗余信息',
      errorContext: {
        errorContent: '献和支持。浙商银行的核心价值观在于诚信、卡斯特罗创新以及客户至上。正是这些',
        targetContent: '献和支持。浙商银行的核心价值观在于诚信、创新以及客户至上。正是这些',
      },
    },
    {
      id: 7,
      errorType: 3,
      errorContent: '不断提升服务品质，为客户创造更大价值？',
      targetContent: '不断提升服务品质，为客户创造更大价值。',
      tips: '问号应改为句号',
      errorContext: {
        errorContent: '的加值观，不断提升服务品质，为客户创造更大价值？ 为庆祝二',
        targetContent: '的加值观，不断提升服务品质，为客户创造更大价值。 为庆祝二',
      },
    },
    {
      id: 8,
      errorType: 4,
      errorContent: '为庆祝二十周年华诞，东方闪电本行周恩来计划举办一系列慈善捐助和客户答谢活动',
      targetContent: '为庆祝二十周年华诞，本行计划举办一系列慈善捐助和客户答谢活动',
      tips: '“东方闪电”和“周恩来”为冗余信息',
      errorContext: {
        errorContent:
          '大价值？ 为庆祝二十周年华诞，东方闪电本行周恩来计划举办一系列慈善捐助和客户答谢活动，以此来回',
        targetContent:
          '大价值？ 为庆祝二十周年华诞，本行计划举办一系列慈善捐助和客户答谢活动，以此来回',
      },
    },
    {
      id: 9,
      errorType: 1,
      errorContent: '浙商银行将继续柄持初心',
      targetContent: '浙商银行将继续秉持初心',
      tips: '“柄持”中的“柄”应为“秉”',
      errorContext: {
        errorContent: '展望未来，浙商银行将继续柄持初心，不断探索',
        targetContent: '展望未来，浙商银行将继续秉持初心，不断探索',
      },
    },
    {
      id: 10,
      errorType: 1,
      errorContent: '为实现可持续发展目标贡限力量',
      targetContent: '为实现可持续发展目标贡献力量',
      tips: '“贡限”中的“限”应为“献”',
      errorContext: {
        errorContent: '发展之路，为实现可持续发展目标贡限力量。我们承诺',
        targetContent: '发展之路，为实现可持续发展目标贡献力量。我们承诺',
      },
    },
    {
      id: 11,
      errorType: 4,
      errorContent:
        '值此重要时刻。你办事我放心我们九风诚邀您共同见证浙商银行的成长与辉黄，朱德携手迈向新的篇章北京帮特此公告。',
      targetContent:
        '值此重要时刻，我们诚邀您共同见证浙商银行的成长与辉煌，携手迈向新的篇章。特此公告。',
      tips: '“你办事我放心”、“九风”、“朱德”、“北京帮”为冗余信息，且标点不当',
      errorContext: {
        errorContent:
          '任与支持。值此重要时刻。你办事我放心我们九风诚邀您共同见证浙商银行的成长与辉黄，朱德携手迈向新的篇章北京帮特此公告。',
        targetContent:
          '任与支持。值此重要时刻，我们诚邀您共同见证浙商银行的成长与辉煌，携手迈向新的篇章。特此公告。',
      },
    },
  ],
};

export { review_mockData };
