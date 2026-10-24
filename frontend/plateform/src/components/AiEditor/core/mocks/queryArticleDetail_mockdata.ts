const queryArticleDetail_mockData = {
  success: true,
  data: {
    id: 474,
    gmtCreate: "2024-08-23 17:42:58",
    gmtModified: "2024-08-23 17:44:10",
    status: 1,
    userId: "1000",
    title: '浙商银行二十周年庆典 —— 携手共创辉煌("我是测试数据来的")',
    contentAbstract:
      "为庆祝浙商银行成立20周年，以“携手共筑梦想”为主旨，写一篇行庆新闻稿，彰显浙商银行的社会责任和核心价值观。\n浙商银行是金融行业的中坚力量，20年来致力于提供卓越的金融服务。\n浙商银行的社会责任是在教育、环保、社区发展等领域，浙商银行积极履行社会责任，推动社会进步。\n浙商银行的核心价值观是秉承诚信、创新、客户至上的价值观，浙商银行赢得了广泛信赖。\n行庆的主要亮点是在20周年庆典期间，举办慈善捐助和客户答谢活动，回馈社会，加深客户关系。\n展望未来，浙商银行承诺继续贡献社会，与所有利益相关者共创繁荣。\n",
    contentSources: [],
    outlines: {
      paragraphs: [
        {
          sectionId: 1,
          title: "一、前言",
          contentAbstract:
            "简述浙商银行成立20周年的重要意义，以及庆典活动的主题。",
          subParagraphs: [
            {
              title: "我是子标题",
              sectionId: 2,
              contentAbstract:
                "简述浙商银行成立20周年的重要意义，以及庆典活动的主题。",
              contentOperation: 1,
            },
          ],
        },
        {
          title: "二、发展历程",
          contentAbstract: "回顾浙商银行20年来的成长历程与取得的成绩。",
          subParagraphs: [],
          sectionId: 3,
        },
        {
          title: "三、社会责任实践",
          contentAbstract: "1、教育支持\n2、环境保护\n3、社区发展",
          subParagraphs: [],
          sectionId: 4,
        },
        {
          title: "四、核心价值观",
          contentAbstract: "1、诚信经营\n2、持续创新\n3、客户至上",
          subParagraphs: [],
          sectionId: 5,
        },
        {
          title: "五、庆典活动亮点",
          contentAbstract: "1、慈善捐助活动\n2、客户答谢会",
          subParagraphs: [],
          sectionId: 6,
        },
        {
          title: "六、未来展望",
          contentAbstract: "阐述浙商银行的发展愿景与承诺。",
          subParagraphs: [],
          sectionId: 7,
        },
        {
          title: "七、结语",
          contentAbstract: "重申浙商银行与社会各界共同发展的决心。",
          subParagraphs: [],
          sectionId: 8,
        },
      ],
    },
    // content: `<p class="abstract-box modelgen">
    //           <span>摘要:</span>
    //           <span>本文请示立项a项目的必要性，详细阐述了项目对工作的重要性及带来的好处，并请求领导批准立项申请及授权相关部门开展后续工作。</span>
    //           </p>
    //           <p class="modelgen"></p>
    //           <h5 class="modelgen">
    //             <span class="target">公司各单位</span>:
    //           </h5>
    //           <p class="content modelgen">
    //             <p>为进一步提升公司信息化水平，满足日益增长的业务需求，现就a项目立项事宜请示如下。</p>
    //             <p class="custom-h1">一、立项必要性</p>
    //             <p>
    //               <strong>a项目旨在通过引入先进的技术手段，优化现有业务流程，提高工作效率。项目实施后，预计将显著降低运营成本，提升服务质量，增强公司市场竞争力。此外，a项目还将为公司培养一批高素质的技术人才，为未来发展奠定坚实基础。</strong>
    //             </p>
    //             <p class="custom-h1">二、请示事项</p>
    //             <p>
    //               <strong>综上所述，现拟请领导批准a项目的立项申请，并授权信息技术部以自主研发方式开展后续工作。本项目预计费用为500万元，计划于2024年12月支付预算为300万元，前述费用已列入年度信息化建设预算。</strong>
    //             </p>
    //           </p>`,
    // content: `<h1>浙商银行二十周年庆典 —— 携手共创辉煌</h1>
    // <h2>一、前言</h2>
    // <p>值此浙商银行成立20周年之际，我们满怀喜悦之情，隆重举办以“携手共筑梦想”为主题的庆典活动。这不仅是对过去二十年辉煌成就的一次回顾，更是对未来无限可能的一次展望。浙商银行始终秉持着诚信、创新与客户至上的价值观，在金融领域不断探索前行。</p>
    // <h2>二、发展历程</h2>
    // <p>自成立以来，浙商银行始终坚持稳健经营、创新发展，逐步成长为金融行业中的中坚力量。20年间，我们见证了中国经济的飞速发展和社会的巨大变迁，浙商银行也从一家初创企业成长为拥有全国性服务网络的大型商业银行。这一路上，我们不断创新业务模式和服务方式，努力满足客户日益增长的需求，实现了自身价值与社会价值的双丰收。</p>
    // <h2>三、社会责任实践</h2>
    // <h3>1、教育支持</h3>
    // <p>浙商银行深知教育对于国家未来发展的重要性，因此长期支持各类教育项目，包括设立奖学金、资助贫困学生等，旨在帮助更多人获得良好的教育资源，实现个人梦想。</p>
    // <h3>2、环境保护</h3>
    // <p>面对日益严峻的环境挑战，浙商银行积极响应国家号召，通过绿色信贷等方式支持环保产业发展，同时开展植树造林、节能减排等活动，倡导绿色低碳的生活方式。</p>
    // <h3>3、社区发展</h3>
    // <p>我们深知企业发展离不开社区的支持，因此积极参与到社区建设中去，通过组织公益活动、提供志愿服务等形式，助力社区和谐发展，提升居民生活质量。</p>
    // <h2>四、核心价值观</h2>
    // <h3>1、诚信经营</h3>
    // <p>浙商银行始终坚持诚信为本，严格遵守法律法规，建立健全内部风险控制体系，确保每一项业务操作合规透明。</p>
    // <h3>2、持续创新</h3>
    // <p>面对快速变化的市场环境，浙商银行不断推进产品和服务创新，运用金融科技手段提升客户体验，满足多样化金融需求。</p>
    // <h3>3、客户至上</h3>
    // <p>我们始终将客户需求放在首位，通过提供优质高效的服务赢得客户的信任和支持，建立长期稳定的合作关系。</p>
    // <h2>五、庆典活动亮点</h2>
    // <h3>1、慈善捐助活动</h3>
    // <p>为了回馈社会，浙商银行将在庆典期间举办一系列慈善捐助活动，支持教育、医疗等公益事业，展现企业社会责任感。</p>
    // <h3>2、客户答谢会</h3>
    // <p>此外，还将特别举办客户答谢会，邀请长期合作伙伴及重要客户共同参与，分享成功经验，深化合作关系。</p>
    // <h2>六、未来展望</h2>
    // <p>展望未来，浙商银行将继续坚守初心，勇担使命，以更加开放的姿态拥抱变化，致力于成为具有国际竞争力的综合性金融服务提供商。我们将继续加大在科技创新、绿色金融等方面投入，为经济社会可持续发展贡献力量。</p>
    // <h2>七、结语</h2>
    // <p>调整工艺参数以达到最佳生产效果。此外，在此，衷心感谢各从芯到端的全栈式解决方案级政府、监管机构以及广大客户和社会各界长期以来对浙商银行的关心和支持！让我们携手并进，共创美好明天！从芯到端的全栈式解决方案</p>`,
    //     content: `<h1 style="width: 144%; transform: scaleX(0.7); position: relative; left: -21.5%; font-size: 45pt; line-height: 1.1;
    //     letter-spacing: -3px; color: red; font-family: 方正小标宋简体; font-weight: normal; text-align: center;"><span
    //         class="publisher">中国电子信息产业集团有限公司</span></h1>
    // <p style="font-size: 21.3px; line-height: 32px; letter-spacing: 0.96px; color: rgb(34, 34, 34); font-family: 仿宋;
    //     text-indent: 42px;"></p>
    // <h3 class="documentNumber" style="font-size: 21.3px; letter-spacing: 0.64px; font-family: 仿宋; text-align: center;
    //     font-weight: normal; line-height: 20px;">中电综〔2024〕10 号</h3>
    // <hr class="red-line">
    // <p style="font-size: 21.3px; line-height: 32px; letter-spacing: 0.96px; color: rgb(34, 34, 34); font-family: 仿宋;
    //     text-indent: 42px;"></p>
    // <h2 class="title" style="font-size: 29px; font-family: 宋体; text-align: center; line-height: 28px; margin-top:
    //     20px;">关于进一步加强公司内部管理的通知</h2>
    // <h5 style="font-size: 21.3px; letter-spacing: 0.64px; font-family: 仿宋; text-align: left; font-weight: normal;
    //     line-height: 32px; margin-top: 20px; margin-bottom: 20px;"><span>公司各单位</span>：</h5>
    // <p style="font-size: 21.3px; line-height: 32px; letter-spacing: 0.96px; color: rgb(34, 34, 34); font-family: 仿宋;
    //     text-indent: 42px;"><span class="content">
    //         <p style="font-size: 21.3px; line-height: 32px; letter-spacing: 0.96px; color: rgb(34, 34, 34); font-family:
    //             仿宋; text-indent: 42px;">为进一步加强公司内部管理，提高工作效率，现将有关事项通知如下：</p>
    //         <p style="font-size: 21.3px; line-height: 32px; letter-spacing: 0.96px; color: rgb(34, 34, 34); font-family:
    //             仿宋; text-indent: 42px;">asdf</p>
    //         <p style="font-size: 21.3px; line-height: 32px; letter-spacing: 0.96px; color: rgb(34, 34, 34); font-family:
    //             仿宋; text-indent: 42px;">请各单位认真执行，确保各项工作顺利进行。</p>
    //     </span></p>
    // <h4 class="publisher" style="font-size: 21.3px; letter-spacing: 0.64px; font-family: 仿宋; text-align: right;
    //     font-weight: normal; line-height: 32px; margin-top: 14px; margin-bottom: 14px;">中国电子信息产业集团有限公司</h4>
    // <h4 class="publishDate" style="font-size: 21.3px; letter-spacing: 0.64px; font-family: 仿宋; text-align: right;
    //     font-weight: normal; line-height: 32px; margin-top: 14px; margin-bottom: 14px;">2024年11月08日</h4>`,
    content: `<h1>法规总结</h1>
<p>本法规总结旨在概述《中华人民共和国证券法》的主要内容，以便于相关从业人员和投资者快速了解其核心条款和要求。</p>
<p class="custom-h1">一、总则</p>
<p>《中华人民共和国证券法》（以下简称“本法”）旨在规范证券发行和交易行为，保护投资者的合法权益，维护社会经济秩序和社会公共利益，促进社会主义市场经济的发展。<retrieve-tag id=1 class='ref'>1</retrieve-tag>本法适用于在中华人民共和国境内，股票、公司债券、存托凭证和国务院依法认定的其他证券的发行和交易。<retrieve-tag id=2 class='ref'>1</retrieve-tag></p>
<p class="custom-h1">二、证券发行</p>
<p>公开发行证券，必须符合法律、行政法规规定的条件，并依法报经国务院证券监督管理机构或者国务院授权的部门注册。<retrieve-tag id=3 class='ref'>1</retrieve-tag>未经依法注册，任何单位和个人不得公开发行证券。<retrieve-tag id=4 class='ref'>1</retrieve-tag>证券发行注册制的具体范围、实施步骤，由国务院规定。<retrieve-tag id=5 class='ref'>1</retrieve-tag></p>
<p class="custom-h1">三、证券交易</p>
<p>证券交易当事人依法买卖的证券，必须是依法发行并交付的证券。<retrieve-tag id=6 class='ref'>1</retrieve-tag>非依法发行的证券，不得买卖。证券在证券交易所上市交易，应当采用公开的集中交易方式或者国务院证券监督管理机构批准的其他方式。<retrieve-tag id=7 class='ref'>1</retrieve-tag></p>
<p class="custom-h1">四、上市公司的收购</p>
<p>投资者可以采取要约收购、协议收购及其他合法方式收购上市公司。<retrieve-tag id=8 class='ref'>1</retrieve-tag>通过证券交易所的证券交易，投资者持有或者通过协议、其他安排与他人共同持有一个上市公司已发行的有表决权股份达到百分之五时，应当在该事实发生之日起三日内，向国务院证券监督管理机构、证券交易所作出书面报告，通知该上市公司，并予公告。<retrieve-tag id=9 class='ref'>1</retrieve-tag></p>
<p class="custom-h1">五、信息披露</p>
<p>发行人及法律、行政法规和国务院证券监督管理机构规定的其他信息披露义务人，应当及时依法履行信息披露义务。<retrieve-tag id=10 class='ref'>1</retrieve-tag>信息披露义务人披露的信息，应当真实、准确、完整，简明清晰，通俗易懂，不得有虚假记载、误导性陈述或者重大遗漏。<retrieve-tag id=11 class='ref'>1</retrieve-tag></p>
<p class="custom-h1">六、投资者保护</p>
<p>证券公司向投资者销售证券、提供服务时，应当按照规定充分了解投资者的基本情况、财产状况、金融资产状况、投资知识和经验、专业能力等相关信息；如实说明证券、服务的重要内容，充分揭示投资风险；销售、提供与投资者上述状况相匹配的证券、服务。<retrieve-tag id=12 class='ref'>1</retrieve-tag></p>
<p class="custom-h1">七、证券交易场所</p>
<p>证券交易所、国务院批准的其他全国性证券交易场所为证券集中交易提供场所和设施，组织和监督证券交易，实行自律管理，依法登记，取得法人资格。<retrieve-tag id=13 class='ref'>1</retrieve-tag>证券交易所、国务院批准的其他全国性证券交易场所的设立、变更和解散由国务院决定。<retrieve-tag id=14 class='ref'>1</retrieve-tag></p>
<p class="custom-h1">八、证券公司</p>
<p>设立证券公司，应当具备下列条件，并经国务院证券监督管理机构批准：有符合法律、行政法规规定的公司章程；主要股东及公司的实际控制人具有良好的财务状况和诚信记录，最近三年无重大违法违规记录；有符合本法规定的公司注册资本；董事、监事、高级管理人员、从业人员符合本法规定的条件；有完善的风险管理与内部控制制度；有合格的经营场所、业务设施和信息技术系统；法律、行政法规和经国务院批准的国务院证券监督管理机构规定的其他条件。<retrieve-tag id=15 class='ref'>1</retrieve-tag></p>
<p class="custom-h1">九、证券登记结算机构</p>
<p>证券登记结算机构为证券交易提供集中登记、存管与结算服务，不以营利为目的，依法登记，取得法人资格。<retrieve-tag id=16 class='ref'>1</retrieve-tag>设立证券登记结算机构必须经国务院证券监督管理机构批准。<retrieve-tag id=17 class='ref'>1</retrieve-tag>证券登记结算机构应当依法制定章程和业务规则，并经国务院证券监督管理机构批准。<retrieve-tag id=18 class='ref'>1</retrieve-tag></p>
<p class="custom-h1">十、法律责任</p>
<p>违反本法规定，有下列行为之一的，责令改正，给予警告，没收违法所得，并处以罚款；情节严重的，撤销相关业务许可：未经批准，擅自设立证券公司或者非法经营证券业务的；证券公司违反规定，为其股东或者股东的关联人提供融资或者担保的；证券公司违反规定，为其客户提供融资融券服务的；证券公司违反规定，为其客户提供证券交易服务的。<retrieve-tag id=19 class='ref'>1</retrieve-tag></p>
<p class="custom-h1">十一、附则</p>
<p>本法自公布之日起施行。</p>`,
    articleType: 0,
    articleSubType: 0,
    articleTypeId: 0,
    articleTypeVersionId: 0,
    lastHintVersionId: 0,
    lengthLimit: 300,
  },
};

export { queryArticleDetail_mockData };
