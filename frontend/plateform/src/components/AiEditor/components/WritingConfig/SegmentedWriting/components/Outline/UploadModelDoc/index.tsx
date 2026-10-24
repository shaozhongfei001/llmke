import { useCallback, useState, useMemo, useEffect, useRef } from "react";
import {
  Button,
  Tree,
  Modal,
  Tabs,
  Select,
  Popover,
  message,
  Tooltip,
  Input
} from "antd";
import plusBlue from "@/assets/img/plusBlue.png";
import doc from "@/assets/writing/doc.png";
import UploadFileType from "@/pages/HomePage/Writing/EditSegmentedTemplate/components/UploadOne";
import extractFail from "@/assets/img/extractFail.png";
import axios$ from "@/apis";
import OutlineExtractResLayout from "../OutlineExtractRes";
import { CloseOutlined } from "@ant-design/icons";
import SelectMaterialExtract, { getIcon } from "../SelectMaterialExtract";
import {
  CommonBtn,
  PrimaryBtn
} from "@root/src/pages/HomePage/Writing/common/components/PrimaryBtn";
import { useMutation } from "@tanstack/react-query";
import { dealMinioUrl, getCecUrlPrefix } from "@root/src/core/helps";
import { StaticFileReader } from "@mxmweb/fviewer";


const mockData = {
  paragraphs: [
    {
      title: "一、授信方案",
      contentAbstract: "",
      useCustomKb: false,
      useCustomDB: false,
      subParagraphs: [
        {
          title: "（一）本次申报方案",
          contentAbstract:
            "| 借款人 | 全称（简称） |\n| --- | --- |\n| 我行信用评级 |  |\n| 存量客户/新客户 | 存量客户/新客户 |\n| 授信类型 | 一般流动资金贷款/ 1 科创贷等小微产品 |\n| 授信金额 | XX万元（较存量新增 XX 万元） |\n| 期限 |  |\n| 利率 | 固定利率还是浮动利率 （当期LPR加减基点） |\n| 担保方式 | 信用/担保/抵押/质押 |\n| 担保人 | 说明担保人名称（全称）、担保方式、按份担保需明确担保人全称及担保份额 |\n| 抵押物 | 说明抵押物的所有人、位置及面积等基本情况、评估价值、对应的贷款份额、抵押率等 |\n| 质押物 | 说明质押物的所有人、质押物明细、评估价值、对应的贷款份额、质押率等 |\n| 贷款用途 | 简要说明借款人申请贷款的目的，是季节性、临时性资金需求，还是正常生产经营中的经常性占用（含铺底流动资金），对贷款用途的合理性进行详细说明。 |\n| 还款计划 | 说明是否有分期还款计划，每期偿还时间和偿还金额。对于期限超过一年的流动资金贷款，在申报书中明确本金分期还款方案。 |\n| 还款来源 | 该笔贷款的还款来源是经营收入还是其他收入，预估借款人可用于还款资金的金额，能否覆盖我行贷款本息。 |\n| 是否关联方 | 是否我行关联方，如是，需同步报送关联审批材料 |",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: []
        },
        {
          title: "（二）本次申报方案说明",
          contentAbstract:
            "该笔贷款是新增贷款还是还后续贷，本次贷款的期限、利率、担保方式较借款人存量贷款或关联方是否有显著变化，如有请说明理由。目前的利率的浮动标准是否符合有关规定，是否考虑了本行筹资成本、收益及风险因素。该笔贷款是信用贷款还是保证、抵押或质押贷款，担保方式是否合理，较其他金融机构是否有明显差异。",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: []
        },
        {
          title: "（三）借款人与我行银企合作情况",
          contentAbstract: "",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: [
            {
              title: "1．借款人在我行授信情况",
              contentAbstract:
                "| 借款企业 | 融资机构 | 融资方式 | 授信金额 | 当前有效授信 | 提用余额 | 起止日期 | 利率/保证金比 | 担保方式 |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n|  |  |  |  |  |  |  |  |  |\n该笔贷款如审批通过，借款人在我行授信金额变化，是否突破我行集中度相关要求。",
              useCustomKb: false,
              useCustomDB: false,
              subParagraphs: []
            },
            {
              title: "2．借款人在我行结算情况",
              contentAbstract:
                "| 借款企业 | 我行授信 | 企业授信总额 | 我行授信占比 | 我行一手结算回行 | 营业收入 | 回行占比 | 年日均 | 备注 |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n|  |  |  |  |  |  |  |  | 说明我行存款主要为一手、二手结算还是临时性资金 |\n|  |  |  |  |  |  |  |  |  |\n简单说明借款人与我行的合作关系及银行相关效益情况，包括发放本笔贷款可能给我行在结算、中间业务、财资系统、工资代发等方面带来的相关效益。",
              useCustomKb: false,
              useCustomDB: false,
              subParagraphs: []
            }
          ]
        },
        {
          title: "（四）借款人所在集团我行授信情况",
          contentAbstract:
            "| 集团编号 |  | 集团名称 |  |\n| --- | --- | --- | --- |\n| 集团主办行 |  | 集团类型 | 一类/二类集团 |\n| 统一授信额度 |  | 口授信额度 |  |\n| 压降额度 |  | 提用余额 |  |\n该笔贷款如审批通过，借款人所在集团在我行授信金额变化，是否突破我行集中度相关要求。",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: []
        },
        {
          title: "（五）该笔贷款是否符合我行信贷政策",
          contentAbstract:
            "该笔贷款是否符合我行现行的信贷政策，是否属于绿色信贷。若该笔贷款与我行现行的信贷政策或业务惯例有重大不一致的，应重点予以说明。",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: []
        }
      ]
    },
    {
      title: "二、借款人评价",
      contentAbstract: "",
      useCustomKb: false,
      useCustomDB: false,
      subParagraphs: [
        {
          title: "（一）借款人情况",
          contentAbstract: "",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: [
            {
              title: "1．基本情况",
              contentAbstract:
                "包括说明借款人名称、成立时间、注册地址、法定代表人注册资本及各股东单位投资到位情况、经营范围等。\n| 股东名称 | 认缴出资金额 | 认缴比例 | 实缴金额 | 出资方式 |\n| --- | --- | --- | --- | --- |\n|  |  |  |  | 货币/实物 |\n|  |  |  |  |  |\n（如有）历史沿革：成立之初至今实际控制人、法定代表人、股权组成、经营范围变更等历史介绍。",
              useCustomKb: false,
              useCustomDB: false,
              subParagraphs: []
            },
            {
              title: "2．外部资信情况",
              contentAbstract:
                "如有外部信用评级报告，请介绍外部评级结果、展望情况，及主要评价等。如借款人为上市公司，请介绍报告日最新的股价情况、市值情况、市盈率等指标情况。",
              useCustomKb: false,
              useCustomDB: false,
              subParagraphs: []
            },
            {
              title: "3．股东情况",
              contentAbstract:
                "包括借款人的股权结构图、主要股东或实际控制人实力介绍。股权结构图须穿透到最终的实际控制人，需标明各出资人的出资比例（如出资人较为分散，则仅需列示主要的出资人）。若有风投等投资公司进入，需补充股权取得成本、投资款到位情况、是否存在对赌协议及主要内容，判断对赌条款近期触发的可能性以及对借款人经营和财务安全性的影响。",
              useCustomKb: false,
              useCustomDB: false,
              subParagraphs: []
            },
            {
              title: "4．公司治理情况",
              contentAbstract:
                "包括借款人的组织架构及核心管理人员情况。借款人董事会成员构成、实际控制人、法定代表人、财务负责人等核心人员介绍。",
              useCustomKb: false,
              useCustomDB: false,
              subParagraphs: []
            },
            {
              title: "5．资金管理情况",
              contentAbstract:
                "借款人对资金是否具有独立使用权，是否受母公司或集团财务公司统调，是否被关联方占用，是否有公司资金存放个人卡的情况。",
              useCustomKb: false,
              useCustomDB: false,
              subParagraphs: []
            }
          ]
        },
        {
          title: "（二）关联方情况",
          contentAbstract:
            "描述借款人所在集团的概况或者与借款人有密切联系的关联公司（包括股东、子公司、联营企业）的简要状况。说明关联方的基本情况，目前的经营状况、资产状况、财务状况和银行负债情况等。\n关联方明细表如下（单位：万元）：\n| 关联类型 | 公司名称 | 注册资本 | 股东组成 | 主营业务 |\n| --- | --- | --- | --- | --- |\n|  |  |  |  |  |\n|  |  |  |  |  |\n根据20XX 年报表，关联方财务情况如下（单位：万元）：\n| 关联关系 | 公司名称 | 总资产 | 资产负债率营业收入 |  | 净利润 | 银行负债/对外担保 |\n| --- | --- | --- | --- | --- | --- | --- |\n| 控股子公司 |  |  |  |  |  |  |\n| 参股公司 |  |  |  |  |  |  |\n| 其他关联关系 |  |  |  |  |  |  |",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: []
        }
      ]
    },
    {
      title: "三、行业分析",
      contentAbstract:
        "结合业务具体情况分析，对行业运行情况、运行特点、行业周期性、上下游情况、未来发展前景、市场集中度、进入壁垒、行业政策等进行调查与分析。\n针对金额较大的客户，还需提供借款人与同类型上市公司经营、财务数据对比情况，判断借款人在经营方面、财务方面是否具备一定优势。\n针对小微客户，可简要介绍。",
      useCustomKb: false,
      useCustomDB: false,
      subParagraphs: []
    },
    {
      title: "四、经营分析",
      contentAbstract: "",
      useCustomKb: false,
      useCustomDB: false,
      subParagraphs: [
        {
          title: "（一）生产经营介绍",
          contentAbstract: "",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: [
            {
              title: "1．经营模式",
              contentAbstract:
                "包括借款人的经营类型（生产性企业还是贸易型企业），经营模式（自营、代理等）、核心竞争力、获得的发明专利、经营许可（如生产经营许可证、建筑行业资质证书等）、含金量较高的资质或奖励（如专精特新小巨人等）介绍。",
              useCustomKb: false,
              useCustomDB: false,
              subParagraphs: []
            },
            {
              title: "2．产品及收入情况",
              contentAbstract:
                "主要产品介绍、产品功能、使用场景等。主要产品的产销率、销售收入增长率、销售利润增长率、市场占有率、出口创汇能力等。主要产品的发展前景、经济寿命期、市场前景，管理层对未来发展拟采取的对策等。\n借款人近三年及一期收入及构成：\n| 产品 | 20XX年 | 20XX年 | 20XX年 | 20XX年1-X月 |\n| --- | --- | --- | --- | --- |\n| 入 | 收占比 | 毛利率 | 入 | 收占比 | 毛利率 | 收入 | 占比 | 毛利率 | 入 | 收占比 | 毛利率 |\n| 产品1 |  |  |  |  |  |  |  |  |  |  |  |  |\n| 产品2 |  |  |  |  |  |  |  |  |  |  |  |  |\n| 合计 |  |  |  |  |  |  |  |  |  |  |  |  |",
              useCustomKb: false,
              useCustomDB: false,
              subParagraphs: []
            },
            {
              title: "3．生产情况（非生产型企业该部分可省略）",
              contentAbstract: "",
              useCustomKb: false,
              useCustomDB: false,
              subParagraphs: [
                {
                  title: "（1）生产场地及车间情况",
                  contentAbstract:
                    "包括借款人生产场地及车间情况，位置，面积，自建还是租用等。如是自建厂房，需说明整体投资情况、是否投建完毕，资金来源、资金缺口等，以及未来是否有改扩建计划，以及后续维护或更新成本。如是租赁厂房，需说明租赁合同有效期，租金情况，出租方是否稳定，有无临时要求退租风险。",
                  useCustomKb: false,
                  useCustomDB: false,
                  subParagraphs: []
                },
                {
                  title: "（2）生产工艺及产能情况",
                  contentAbstract:
                    "包括借款人生产所采用工艺、设备的先进水平（设备技术先进性以及设备的新旧程度情况），产能、产量、销量水平，电费等能源消耗情况。\n| 产品 | 设计产能 | 上年产量 | 产能利用率 | 上年销量 | 产销率 |\n| --- | --- | --- | --- | --- | --- |\n| 产品1 |  |  |  |  |  |\n| 产品2 |  |  |  |  |  |\n| 合计 |  |  |  |  |  |\n（3）环评情况\n包括借款人是否取得合法合规的环评手续，是否有环评风险。",
                  useCustomKb: false,
                  useCustomDB: false,
                  subParagraphs: []
                }
              ]
            },
            {
              title: "4．成本组成",
              contentAbstract:
                "包括公司产品主要的成本和费用组成，核心原材料渠道和价格的依赖程度，原材料价格变动对成本的影响和评价。如借款人对资源（水、电、气等）价格较为敏感，需介绍资源价格对借款人生产经营的影响。如借款人成本构成中人员占比较大，需在下文“人员组成情况”中进行详细说明。",
              useCustomKb: false,
              useCustomDB: false,
              subParagraphs: []
            },
            {
              title: "5．上游供应商情况",
              contentAbstract:
                "包括借款人近两至三年供应商组成，借款人前五大供应商（如果供应商较为分散，请提供前十大供应商）列表，分析主要供应商背景、渠道稳定性、供应材料类型、主要结算方式等。\n| 序号 | 供应商名称 | 供应商背景 | 对应项目（如有） | 采购金额 | 占比 | 采购内容 | 结算方式及账期 | 备注 |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n| 1 |  |  |  |  |  |  |  |  |\n| 2 |  |  |  |  |  |  |  |  |\n| 3 |  |  |  |  |  |  |  |  |\n| 4 |  |  |  |  |  |  |  |  |\n| 5 |  |  |  |  |  |  |  |  |\n| 合计 |  |  |  |  |  |  |  |  |",
              useCustomKb: false,
              useCustomDB: false,
              subParagraphs: []
            },
            {
              title: "6．下游客户情况",
              contentAbstract:
                "包括借款人近两至三年客户组成，借款人前五大客户（如果客户较为分散，请提供前十大客户）列表，分析主要客户背景、渠道稳定性、销售产品类型、主要结算方式等。\n| 序号 | 下游客户名称 | 客户背景 | 对应项目（如有） | 销售金额 | 占比 | 销售内容 | 结算方式及账期 | 备注 |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n| 1 |  |  |  |  |  |  |  |  |\n| 2 |  |  |  |  |  |  |  |  |\n| 3 |  |  |  |  |  |  |  |  |\n| 4 |  |  |  |  |  |  |  |  |\n| 5 |  |  |  |  |  |  |  |  |\n| 合计 |  |  |  |  |  |  |  |  |",
              useCustomKb: false,
              useCustomDB: false,
              subParagraphs: []
            },
            {
              title: "7．在手订单情况",
              contentAbstract:
                "介绍借款人目前在手订单和拟签订情况，需说明是框架合同还是执行合同订单，并根据在手订单情况预计未来销售收入变化。",
              useCustomKb: false,
              useCustomDB: false,
              subParagraphs: []
            },
            {
              title: "8．关联交易情况",
              contentAbstract:
                "如借款人上下游关联交易占比较大，请说明关联交易在采购或销售额中的占比，采购和销售的内容及合理性、定价的公允性。",
              useCustomKb: false,
              useCustomDB: false,
              subParagraphs: []
            },
            {
              title: "9．重大投资情况",
              contentAbstract:
                "包括近期是否有重大的对外投资、厂区建设、收购并购等重大投资，总投资金额，分年投资计划、资金来源等。",
              useCustomKb: false,
              useCustomDB: false,
              subParagraphs: []
            }
          ]
        },
        {
          title: "（二）其他经营相关情况",
          contentAbstract: "",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: [
            {
              title: "1．人员组成情况",
              contentAbstract:
                "包括人员数量（其中缴纳社保人数）、人员结构等。如借款人是人员密集型企业（如设计公司），需介绍人员结构、工资水平、人员稳定性等，并分析对公司经营的影响。如借款人是高新技术企业，需介绍核心技术人员情况及稳定性，并分析核心人员变动对公司经营的影响。",
              useCustomKb: false,
              useCustomDB: false,
              subParagraphs: []
            },
            {
              title: "2．纳税情况",
              contentAbstract:
                "包括我行是否获得借款人税务授权，借款人近三年的增值税、所得税纳税情况，与报表收入是否匹配，是否有税务风险。\n| 是否取得税务授权 | 是/否 |\n| --- | --- |\n| 项目 | 月 | 20XX 年 1-1220XX 年1-12 月 | 20XX年1-X月 |\n| 报表：主营业务收入 |  |  |  |\n| 增值税申报书：纳税收入 |  |  |  |\n| 增值税实际缴纳税额 |  |  |  |\n| 所得税申报书：纳税收入 |  |  |  |\n| 所得税实际缴纳税额 |  |  |  |",
              useCustomKb: false,
              useCustomDB: false,
              subParagraphs: []
            },
            {
              title: "3．银行流水情况",
              contentAbstract:
                "包括主要结算行流水情况，通过银行承兑汇票/商业承兑汇票等结算情况，与报表收入是否匹配，是否有虚高收入风险。\n| 项目 | 月 | 20XX 年 1-1220xx 年 1-1220xx 年 1-X 月 | 月 |\n| --- | --- | --- | --- |\n| 报表：主营业务收入 |  |  |  |\n| 流水情况（现金） |  |  |  |\n| 流水情况（票据） |  |  |  |\n| 其中：银行承兑汇票 |  |  |  |\n| 商业承兑汇票 |  |  |  |\n| 流水小计 |  |  |  |",
              useCustomKb: false,
              useCustomDB: false,
              subParagraphs: []
            }
          ]
        }
      ]
    },
    {
      title: "五、财务分析",
      contentAbstract: "",
      useCustomKb: false,
      useCustomDB: false,
      subParagraphs: [
        {
          title: "（一）报表情况",
          contentAbstract:
            "借款人报表口径（合并报表/单体报表），报表范围（合并范围内的主要子公司，以及近期有无变化），报表审计情况（审计的会计事务所及审计意见等）。",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: []
        },
        {
          title: "（二）财务报表",
          contentAbstract:
            "| 报表科目 | -3 | -2 | -1 | 0（当期） | 报表备注 |\n| --- | --- | --- | --- | --- | --- |\n| 总资产 |  |  |  |  |  |\n| 流动资产 |  |  |  |  |  |\n| 货币资金 |  |  |  |  |  |\n| 应收账款 |  |  |  |  |  |\n| 应收票据 |  |  |  |  |  |\n| 合同资产 |  |  |  |  |  |\n| 其他应收款 |  |  |  |  |  |\n| 存货 |  |  |  |  |  |\n| 非流动资产 |  |  |  |  |  |\n| 长期股权投资 固定资产原值 |  |  |  |  |  |\n| 折旧 |  |  |  |  |  |\n| 固定资产净值 |  |  |  |  |  |\n| 在建工程 |  |  |  |  |  |\n| 无形资产 |  |  |  |  |  |\n| 总负债 |  |  |  |  |  |\n| 流动负债 |  |  |  |  |  |\n| 短期借款 |  |  |  |  |  |\n| 应付账款 |  |  |  |  |  |\n| 预收账款 |  |  |  |  |  |\n| 合同负债 |  |  |  |  |  |\n| 一年内到期的长期负债 |  |  |  |  |  |\n| 长期负债 |  |  |  |  |  |\n| 长期借款 |  |  |  |  |  |\n| 应付债券 |  |  |  |  |  |\n| 长期应付款 |  |  |  |  |  |\n| 所有者权益 |  |  |  |  |  |\n| 实收资本（股本） |  |  |  |  |  |\n| 资本公积 未分配利润 |  |  |  |  |  |\n| 销售收入 |  |  |  |  |  |\n| 销售成本 |  |  |  |  |  |\n| 销售费用 |  |  |  |  |  |\n| 管理费用 |  |  |  |  |  |\n| 研发费用 |  |  |  |  |  |\n| 财务费用 |  |  |  |  |  |\n| 销售利润 |  |  |  |  |  |\n| 其他营业收入 |  |  |  |  |  |\n| 其他营业成本 |  |  |  |  |  |\n| 税前利润 |  |  |  |  |  |\n| 企业所得税 |  |  |  |  |  |\n| 税后利润 经营活动产生的现金流量净额 |  |  |  |  |  |\n| 投资活动产生的现金流量净额 |  |  |  |  |  |\n| 筹资活动产生的现金流量净额 |  |  |  |  |  |\n| 现金流净额 |  |  |  |  |  |\n| 财务指标： |  |  |  |  |  |\n| 流动比 |  |  |  |  |  |\n| 速动比 |  |  |  |  |  |\n| 资产负债率 |  |  |  |  |  |\n| 毛利润率 |  |  |  |  |  |\n| 销售利润率 |  |  |  |  |  |\n| 净利润率 |  |  |  |  |  |\n| 应收账款周转天数 |  |  |  |  |  |\n| 存货周转天数 |  |  |  |  |  |\n| 预付账款周转天数 |  |  |  |  |  |\n| 预收账款周转天数 |  |  |  |  |  |\n| 应付账款周转天数 |  |  |  |  |  |\n| 营运周期 |  |  |  |  |  |\n| 刚性负债 |  |  |  |  |  |\n| 当年分红 |  |  |  |  |  |\n关于报表科目的选择原则及说明：\n1．余额大于总资产5%的科目应当列示在报表项目中，且在报表备注栏说明科目的主要内容及金额；\n2．作为实体经营企业，应收账款、应收票据、预付账款、合同资产、存货、应付账款、应付票据、预收账款、合同负债等经营相关科目必须列示，且须在报表备注栏列出前几大，其中应收账款、应付账款还需列明账龄分布、坏账计提情况；存货列明计提减值情况；应收票据需分别列明银行承兑汇票和商业承兑汇票的金额。\n3．短期借款、一年内到期的非流动负债、长期借款、应付债券、其他应付款（包含融资租赁）等刚性债务科目必须列示。\n4．货币资金在报表备注栏说明受限资金情况，包括保证金等。\n5．固定资产在报表备注栏说明具体内容，且填写原值和累计折旧额。\n6．说明借款人近三年及申请借款前一个月的财务状况及其变化的主要原因，尤其要说明主要财务指标及主要科目异常变化的情况和原因。对财务报表主要指标进行比较分析。",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: []
        },
        {
          title: "（三）财务评价",
          contentAbstract: "",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: [
            {
              title: "1．偿债能力分析",
              contentAbstract:
                "结合借款人的资产负债率、流动比、速动比、资产结构、债务结构等分析借款人的长短期偿债能力。",
              useCustomKb: false,
              useCustomDB: false,
              subParagraphs: []
            },
            {
              title: "2．盈利能力分析",
              contentAbstract:
                "结合借款人的收入稳定性、毛利率水平、期间费用、净利率水平等分析借款人的盈利能力及未来趋势分析。",
              useCustomKb: false,
              useCustomDB: false,
              subParagraphs: []
            },
            {
              title: "3．现金流分析",
              contentAbstract:
                "结合借款人经营性现金流、投资性现金流、筹资性现金流水平分析借款人的现金流获取能力。",
              useCustomKb: false,
              useCustomDB: false,
              subParagraphs: []
            },
            {
              title: "4．周转能力分析",
              contentAbstract:
                "结合借款人应收账款、预付账款、存货、应付账款、预收账款周转天数判断借款人的资金周转能力。",
              useCustomKb: false,
              useCustomDB: false,
              subParagraphs: []
            },
            {
              title: "5．综合评价",
              contentAbstract: "综合上述信息，对借款人整体财务情况进行评价。",
              useCustomKb: false,
              useCustomDB: false,
              subParagraphs: []
            }
          ]
        }
      ]
    },
    {
      title: "六、外部负债情况",
      contentAbstract: "",
      useCustomKb: false,
      useCustomDB: false,
      subParagraphs: [
        {
          title: "（一）银行征信查询",
          contentAbstract:
            "请提供1 个月以内的银行征信查询结果，包括银行贷款情况、对外担保情况、其他不良信息等。",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: []
        },
        {
          title: "（二）借款人全部有息负债情况",
          contentAbstract:
            "截止申请本次贷款时，借款人全部有息负债情况，包括银行贷款、承兑敞口、保理融资、融资租赁、直接融资（包括债券融资）等。\n| 融资企业 | 融资机构 | 融资方式 | 授信金额 | 提用余额 | 起止日期 | 利率/保证金比例 | 担保方式 |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n|  |  |  |  |  |  |  |  |\n|  |  |  |  |  |  |  |  |\n如有长期贷款（包括固贷、融资租赁等）请说明分期还款计划。",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: []
        },
        {
          title: "（三）对外担保情况",
          contentAbstract:
            "借款人对外担保的情况，对外担保金额是否超出借款人的担保能力（如是否超过借款人净资产），分析对外担保的被担保人是否存在违约风险，导致借款人或有负债风险增加。",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: []
        },
        {
          title: "（四）银企合作情况",
          contentAbstract:
            "简单说明借款人与各家银行的合作关系及银行相关效益情况。\n借款人与各家银行合作情况（单位：万元）\n| 金融机构名称 | 本行 | XX 行 | XX 行 | … |\n| --- | --- | --- | --- | --- |\n| 存款户开立情况 |  |  |  |  |\n| 销售收入结算率 |  |  |  |  |\n| 存款余额 |  |  |  |  |\n| 贷款余额 |  |  |  |  |",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: []
        }
      ]
    },
    {
      title: "七、外部不良信息",
      contentAbstract: "",
      useCustomKb: false,
      useCustomDB: false,
      subParagraphs: [
        {
          title:
            "（一）借款人及关联方是否存在逾期、欠息等不良信息，以及是否存在账户查封、被纳入失信被执行人等信息",
          contentAbstract: "",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: []
        },
        {
          title:
            "（二）借款人及关联方是否已卷入或即将卷入重大的诉讼或仲裁程序及其他法律纠纷等",
          contentAbstract: "",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: []
        },
        {
          title: "（三）借款人及关联方是否存在外部重大负面舆论信息",
          contentAbstract: "",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: []
        }
      ]
    },
    {
      title: "八、担保方案",
      contentAbstract: "",
      useCustomKb: false,
      useCustomDB: false,
      subParagraphs: [
        {
          title: "（一）担保方案介绍",
          contentAbstract:
            "介绍该笔贷款发放所采取的担保方式，及各担保方式对应的贷款份额。",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: []
        },
        {
          title: "（二）担保人/抵质押物分析",
          contentAbstract:
            "采用第三方连带责任保证方式的，重点分析保证人的经营情况、财务情况、资信状况、代偿能力及对其他企业现有的有效担保情况；\n采用抵（质）押方式的，重点分析抵（质）押物的物类、权属、价值、流动性（变现能力）、可控性、抵（质）押率，是否存有与其他贷款人分享抵押物或借款人在有多个债权人的\n情况下将全部资产抵押给我行的情况；担保期是否与贷款期限相匹配。\n| 抵（质）押人： | 抵（质）押物名称： |\n| --- | --- |\n| 评估价值： | 已为其他债权设定抵（质）押额： |\n| 本笔贷款抵（质）押率： |  |\n| 序号 | 位置 | 所有权人 | 用途 | 权证号 | 占地面积 | 建筑面积 | “三合一” 价值 |\n| --- | --- | --- | --- | --- | --- | --- | --- |\n|  |  |  |  |  |  |  |  |\n由担保公司提供担保的，应说明反担保措施；涉及我行信贷产品的，应列示产品的损失分担比例。",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: []
        },
        {
          title: "（三）担保能力评价",
          contentAbstract:
            "采用信用贷款方式的，需说明采用此方式的理由。\n综合上述担保人、抵质押物等情况，结合担保人的担保意愿、担保能力及抵质押物对贷款的覆盖程度、变现能力分析该笔贷款的担保能力。",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: []
        }
      ]
    },
    {
      title: "九、贷款合理性分析",
      contentAbstract: "",
      useCustomKb: false,
      useCustomDB: false,
      subParagraphs: [
        {
          title: "（一）流动资金需求测算",
          contentAbstract:
            "分支机构可根据借款人当期财务报告和业务发展预测，按以下方法测算其流动资金贷款需求量：\n1．估算借款人营运资金量\n借款人营运资金需求可参考如下公式：\n营运资金量 ＝ 上年度销售收入 ×（1－上年度销售利润率）×（1＋预计销售收入年增长率）/营运资金周转次数\n其中：营运资金周转次数 ＝ 360 / (存货周转天数 + 应收账款周转天数－应付账款周转天数 + 预付账款周转天数－预收账款周转天数)\n周转天数 ＝ 360 / 周转次数\n应收账款周转次数 ＝ 销售收入 / 平均应收账款余额\n预收账款周转次数 ＝ 销售收入 / 平均预收账款余额\n存货周转次数 ＝ 销售成本 / 平均存货余额\n预付账款周转次数 ＝ 销售成本 / 平均预付账款余额\n应付账款周转次数 ＝ 销售成本 / 平均应付账款余额\n2．估算新增流动资金贷款额度\n新增流动资金贷款额度 ＝ 营运资金量－借款人自有资金－现有流动资金贷款－其他渠道提供的营运资金\n备注：若借款人不适用于上述测算公式，如小微企业融资、订单融资、预付租金或者临时大额债项融资等情况，可不采用上述公式，在交易真实性的基础上，确保有效控制用途和回款情况下，根据实际交易需求确定流动资金额度。",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: []
        },
        {
          title: "（二）贷款额度合理性分析",
          contentAbstract:
            "根据借款人所属行业、生产规模、经营特点、发展计划和流动资产周转期等，测算其营运资金量，估算新增流动资金贷款额度。综合考虑借款人实际情况、未来发展情况以及各类融资情形，分析借款人现有流动资金的来源构成、流动资金需求因何增加，该笔贷款投入是否合理，是否超过借款人合理支付能力，能否满足借款人正常运营的需要。借款人资金运营有无季节性，对流动资金贷款的季节性需求等。",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: []
        },
        {
          title: "（三）贷款还款能力评价",
          contentAbstract:
            "借款人的第一还款来源通常为日常经营收入及近期储备的可以锁定的大额订单，根据借款人股东背景、行业前景及经营情况、财务情况、持续融资能力等，综合考虑本次贷款方案（金额、期限、利率、担保等），分析借款人的偿债能力和偿债意愿，判断该笔贷款的信用风险是否可控。\n借款人的第二还款来源通常为担保人的履约能力和抵质押物的变现能力。根据担保人的担保能力和担保意愿，抵质押物的价值对贷款的覆盖水平、变现能力等，判断借款人的第二还款意愿及还款能力是否可靠。",
          useCustomKb: false,
          useCustomDB: false,
          subParagraphs: []
        }
      ]
    },
    {
      title: "十、本笔贷款法律问题",
      contentAbstract:
        "简要说明本笔贷款在合同、担保、承诺、政府法规等方面是否存有需要澄清和解决的法律问题。包括法定代表人无法签订贷款合同、无法办理我行标准的应收账款质押、已婚实际控制人仅提供个人担保等。",
      useCustomKb: false,
      useCustomDB: false,
      subParagraphs: []
    },
    {
      title: "十一、风险提示与防范措施",
      contentAbstract:
        "分析借款人生产经营风险状况及相应的防范措施。包括借款人在生产经营过程中存在的行业、市场、经营等风险，是否引起管理层的重视，已经采取或准备采取的措施及效果；尚存风险及拟采取的措施；针对贷款投入后的主要风险因素，我行拟采取降低或规避风险的措施。",
      useCustomKb: false,
      useCustomDB: false,
      subParagraphs: []
    },
    {
      title: "十二、分支机构意见",
      contentAbstract:
        "说明分支机构对该项贷款的决策意见，明确表达同意发放或否决的意见，贷款的具体方案（金额、期限、利率、担保方式、还款方式等）。",
      useCustomKb: false,
      useCustomDB: false,
      subParagraphs: []
    }
  ],
  allSectionIds: [],
  allLeafSectionIds: [],
  sectionDependency: {}
};

enum OutlineMethod {
  Material,
  Upload
}
const extractOutlineMethod = [
  {
    label: "从素材库选择",
    value: OutlineMethod.Material
  },
  {
    label: "上传模版文档",
    value: OutlineMethod.Upload
  }
];

const titleMap = {
  0: "一",
  1: "二",
  2: "三",
  3: "四",
  4: "五",
  5: "六",
  6: "七",
  7: "八",
  8: "九",
  9: "十"
};

const options = [
  { value: "一、", label: "一、标题名称" },
  { value: "（一）", label: "（一）标题名称" },
  { value: "1.", label: "1. 标题名称" },
  { value: "（1）", label: "（1）标题名称" }
];

const renderNode = ({
  node,
  handleShowContentAbstract,
  curExtractMethod
}: any) => {
  const spanDom =
    node?.title?.length > 50 ? (
      <span
        className="w-full"
        onClick={() => {
          handleShowContentAbstract(node);
        }}
      >
        {node?.title.substring(0, 49) + "..."}
      </span>
    ) : (
      <span
        onClick={() => {
          handleShowContentAbstract(node);
        }}
      >
        {node?.title}
      </span>
    );

  if (curExtractMethod === OutlineMethod.Upload) {
    return spanDom;
  } else {
    const isLeaf = !node?.subParagraphs || !node?.subParagraphs?.length;
    if (isLeaf) {
      console.log("=====");
      return (
        <Tooltip title={"点击可查看内容要求"} placement="top">
          {spanDom}
        </Tooltip>
      );
    }
    return spanDom;
  }
};

const UploadModelDoc = ({
  applyOutlines,
  disabled = false,
  materialTreeData
}: any) => {
  // 用于关闭弹窗取消请求，大模型接口很慢
  const cancelRequestController = useRef(new AbortController());
  // 不同的抽取方式
  const [curExtractMethod, setCurExtractMethod] = useState<OutlineMethod>();
  const [showPreviewModal, setShowPreviewModal] = useState<boolean>(false);
  const [activeKey, setActiveKey] = useState("1");
  const [titleList, setTitleList] = useState([
    {
      label: "一级标题",
      value: ""
    },
    {
      label: "二级标题",
      value: ""
    },
    {
      label: "三级标题",
      value: ""
    }
  ]);
  const [extractRes, setExtractRes] = useState<any>(); //抽取结果
  const [file, setFile] = useState<any>();
  const [uploadModalOpen, setUploadModalOpen] = useState<boolean>(false);

  const cancelRequest = () => {
    console.log(cancelRequestController.current);
    if (!cancelRequestController.current) return;
    cancelRequestController.current.abort();
    cancelRequestController.current = new AbortController();
  };

  const uploadSeq = async () => {
    const formData = new FormData();
    if (curExtractMethod === OutlineMethod.Upload) {
      formData.append("file", file.originFile);
    } else {
      formData.append("fileId", activeFile.key);
    }
    const titleExamples: any = [];
    titleList.forEach((t) => {
      if (t.value?.length > 0) return titleExamples.push(t.value);
    });
    if (titleExamples.length) {
      formData.append("titleExamples", titleExamples);
    }

    try {
      setReExtractLoading(true);

      const res = await axios$.post(
        `${getCecUrlPrefix()}/dw/articleType/genOutlinesByDocx`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data"
          }
        }
      );
      if (res) {
        setExtractRes(res.data);
        setActiveKey("1");
      }
      setReExtractLoading(false);
    } catch (error) {
      setReExtractLoading(false);
      console.log("====================================");
      console.log("error", error);
      console.log("====================================");
    }
  };

  const treeData = useMemo(() => {
    const traverse = (data: any[]) => {
      return (data || []).filter((item: any) => {
        if (item.subParagraphs) {
          item.subParagraphs = traverse(item.subParagraphs);
        }
        item.title = item.title?.trim();
        return item.title !== "";
      });
    };

    return traverse(extractRes?.paragraphs);
  }, [extractRes?.paragraphs]);

  // 展示内容要求
  const [showContentAbstract, setShowContentAbstract] = useState<any>();
  const handleShowContentAbstract = (node: any) => {
    if (node?.contentAbstract) {
      setShowContentAbstract(node);
    }
  };
  const renderRes = useCallback(() => {
    if (
      extractRes &&
      extractRes?.paragraphs &&
      extractRes?.paragraphs?.length > 0
    ) {
      return (
        <Tree
          fieldNames={{
            title: "title",
            key: "title",
            children: "subParagraphs"
          }}
          titleRender={(node) => {
            return renderNode({
              node,
              handleShowContentAbstract,
              curExtractMethod
            });
          }}
          treeData={treeData}
        />
      );
    } else {
      return (
        <div className="w-full h-[450px] flex flex-col items-center justify-center">
          <img src={extractFail} className="w-[130px] h-[120px]" />
          <div className="mt-[16px]">
            抽取结果失败，建议先
            <span
              className="text-[#055AFF] cursor-pointer"
              onClick={() => {
                setActiveKey("2");
              }}
            >
              配置规则
            </span>
          </div>
        </div>
      );
    }
  }, [extractRes, curExtractMethod]);

  const closeModal = () => {
    setTitleList([
      {
        label: "一级标题",
        value: ""
      },
      {
        label: "二级标题",
        value: ""
      },
      {
        label: "三级标题",
        value: ""
      }
    ]);
    setShowPreviewModal(false);
  };

  const [applyLoading, setApplyLoading] = useState(false);
  const applyApp = async () => {
    setApplyLoading(true);
    try {
      const res = await applyOutlines({
        paragraphs: treeData
      });
      if (res) {
        setShowPreviewModal(false);
      }
      setApplyLoading(false);
    } catch (e) {
      setApplyLoading(false);
    }
  };

  const renderRule = ({ options, titleMap, titleList }: any) => {
    return (
      <>
        <div className="w-full flex flex-row justify-between items-center mb-[10px]">
          <span className="text-sm text-gray-2a font-bold ">标题样式配置</span>
          <Button
            size="small"
            className="text-text-color2 border-[#EEEEEE] w-[94px] text-[12px] flex-row items-center"
            icon={<img src={plusBlue} className="w-[12px] h-[12px] mt-[4px]" />}
            onClick={() => {
              setTitleList((pre) => [
                ...pre,
                {
                  label: `${titleMap[pre.length]}级标题`,
                  value: ""
                }
              ]);
            }}
          >
            添加标题
          </Button>
        </div>
        {titleList.map((title, idx) => {
          return (
            <div className="mb-[10px]" key={`title-${idx}`}>
              <span>{title.label}</span>
              <Select
                style={{
                  width: "100%",
                  height: 32,
                  marginTop: "4px",
                  zIndex: "9999"
                }}
                options={options}
                onChange={(val) => {
                  setTitleList((pre) => {
                    return pre.map((p) => {
                      if (p.label == title.label) {
                        p.value = val;
                      }
                      return p;
                    });
                  });
                }}
                value={title.value}
              />
            </div>
          );
        })}
      </>
    );
  };

  const renderPreview = () => {
    if (file && file?.fileUpload) {
      const parser = new DOMParser();
      const doc = parser.parseFromString(file?.fileUpload, "text/html");
      return doc.body.innerHTML;
    }
    return "";
  };

  const toggleModalHandler = (sta: boolean) => () => {
    setUploadModalOpen(sta);
  };

  const [openSelectMaterial, setOpenSelectModal] = useState<boolean>(false);
  const closeSelectMaterial = () => {
    setOpenSelectModal(false);
    cancelRequest();
    // setActiveFile("");
  };
  const handleExtract = (method: OutlineMethod) => {
    setCurExtractMethod(method);
    setActiveKey("1");
    switch (method) {
      case OutlineMethod.Material:
        setOpenSelectModal(true);
        break;
      case OutlineMethod.Upload:
        setUploadModalOpen(true);
        break;
      default:
        break;
    }
  };
  // 当前选择的文件
  const [activeFile, setActiveFile] = useState<any>("");
  const handleSelectFile = (item: any) => {
    const isFile = item?.elementType === 3;
    isFile && setActiveFile(item);
  };

  const genOutlinesByMaterial = useMutation({
    mutationFn: (fileId: any) =>
      axios$
        .get(`${getCecUrlPrefix()}/dw/articleType/genOutlinesByAgent`, {
          params: {
            fileId
          },
          signal: cancelRequestController.current.signal
        })
        .then((res) => {
          return { ...(res?.data || {}), isCancel: res ? false : true };
        })
  });

  const handleMaterialExtract = async () => {
    if (!activeFile || !activeFile.key) {
      message.error("没有选择文件");
    }
    const res = await genOutlinesByMaterial.mutateAsync(activeFile.key);
    if (res.isCancel) return;
    closeSelectMaterial();
    setShowPreviewModal(true);
    setExtractRes(res);
  };

  const [reExtractLoading, setReExtractLoading] = useState<boolean>(false);

  useEffect(() => {
    setReExtractLoading(genOutlinesByMaterial.isLoading);
  }, [genOutlinesByMaterial.isLoading]);

  const handleReExtract = () => {
    if (OutlineMethod.Upload === curExtractMethod) {
      uploadSeq;
    } else {
      genOutlinesByMaterial.mutateAsync(activeFile.key);
    }
  };

  const isWord = useMemo(() => {
    if (
      activeKey !== "2" ||
      !activeFile ||
      curExtractMethod !== OutlineMethod.Material
    ) {
      return true;
    }
    const name = activeFile.name;
    const isWord = /\.(docx?|DOCX?)$/.test(name);
    if (!isWord) {
      message.info("规则抽取仅支持word文件");
    }
    return isWord;
  }, [activeKey, activeFile, curExtractMethod]);

  return (
    <>
      <Popover
        arrow={false}
        styles={{
          body: {
            padding: "4px"
          }
        }}
        placement="bottomLeft"
        content={
          <div className="w-[126px] box-border">
            {extractOutlineMethod.map((i) => {
              return (
                <div
                  key={i.value}
                  className="py-[5px] px-[12px] hover:bg-[#F1F5FF] cursor-pointer"
                  onClick={() => {
                    handleExtract(i.value);
                  }}
                >
                  {i.label}
                </div>
              );
            })}
          </div>
        }
      >
        <CommonBtn
          disabled={disabled}
          // onClick={toggleModalHandler(true)}
        >
          选择模版文档
        </CommonBtn>
      </Popover>
      <UploadFileType
        open={uploadModalOpen}
        close={toggleModalHandler(false)}
        uploadEvents={(file) => {
          if (file) {
            setUploadModalOpen(false);
            setFile(file);
            setShowPreviewModal(true);
            setExtractRes(file.extractRes);
          }
        }}
      />
      <OutlineExtractResLayout open={showPreviewModal}>
        <div className="w-full h-full box-border overflow-hidden">
          <div
            className="flex justify-between items-center px-[24px] h-[64px]"
            style={{
              boxShadow: "inset 0 8px 8px -8px rgba(0,0,0,0.15)"
            }}
          >
            <div className=" flex flex-row">
              {getIcon({
                name:
                  curExtractMethod === OutlineMethod.Upload
                    ? file?.originFile?.name
                    : activeFile?.name,
                elementType: 3
              })}
              <span className="font-bold text-[16px]">
                {curExtractMethod === OutlineMethod.Upload
                  ? file?.originFile?.name
                  : activeFile?.name}
              </span>
            </div>
            <CloseOutlined className="cursor-pointer" onClick={closeModal} />
          </div>
          <div className="h-[calc(100%-64px)] overflow-y-auto flex flex-row justify-between box-border">
            {curExtractMethod === OutlineMethod.Upload && (
              <div
                className="flex-1 overflow-x-auto bg-[#F0F2F8]"
                dangerouslySetInnerHTML={{ __html: renderPreview() }}
              ></div>
            )}
            {curExtractMethod === OutlineMethod.Material && activeFile && (
              <div className="flex-1 overflow-x-auto bg-[#F0F2F8]">
                <StaticFileReader
                  fileType={(activeFile.convertedFilePath || '').split('.').pop()}
                  fileName={activeFile.name || ""}
                  fileUrl={dealMinioUrl(activeFile.convertedFilePath)}
                  headerClass="bg-white"
                  contentClass="bg-gray-50 p-[12px] md:p-[12px]"
                />
              </div>
            )}
            <div className="flex flex-col w-[420px]">
              <div className="flex-1  overflow-y-auto">
                <Tabs
                  className="custom-tab-box w-full"
                  items={[
                    {
                      key: "1",
                      label: "抽取结果",
                      children: <div className="mt-4">{renderRes()}</div>
                    },
                    {
                      key: "2",
                      label: "配置规则",
                      children: (
                        <div className="mt-4">
                          {renderRule({ options, titleMap, titleList })}
                        </div>
                      )
                    }
                  ]}
                  defaultActiveKey="1"
                  activeKey={activeKey}
                  onChange={(key) => {
                    setActiveKey(key);
                  }}
                  style={{ padding: "0 16px 16px 16px" }}
                ></Tabs>
              </div>
              {activeKey === "1" && (
                <div className="h-[64px] box-border border-0 border-solid border-t-[1px] border-[#EEEEEE] flex justify-end items-center gap-[20px] px-[24px]">
                  <CommonBtn
                    onClick={handleReExtract}
                    loading={reExtractLoading}
                  >
                    重新抽取
                  </CommonBtn>
                  {extractRes &&
                  extractRes?.paragraphs &&
                  extractRes?.paragraphs?.length > 0 ? (
                    <PrimaryBtn
                      // disabled={!activeFile}
                      onClick={applyApp}
                      loading={applyLoading}
                    >
                      应用
                    </PrimaryBtn>
                  ) : (
                    <PrimaryBtn
                      onClick={() => {
                        setActiveKey("2");
                      }}
                    >
                      配置规则
                    </PrimaryBtn>
                  )}
                </div>
              )}
              {activeKey === "2" && (
                <div className="h-[64px] box-border border-0 border-solid border-t-[1px] border-[#EEEEEE] flex justify-end items-center gap-[20px] px-[24px]">
                  <CommonBtn
                    onClick={() => {
                      closeModal();
                    }}
                  >
                    取消
                  </CommonBtn>
                  <PrimaryBtn
                    loading={reExtractLoading}
                    onClick={() => {
                      // 规则抽取,todo
                      uploadSeq();
                    }}
                    disabled={!isWord}
                  >
                    抽取
                  </PrimaryBtn>
                </div>
              )}
            </div>
            {showContentAbstract && (
              <div className="w-[350px] bg-[#F1F5FC] py-[16px] px-[20px] flex flex-col">
                <div className="flex justify-between items-center">
                  <span className="font-bold text-[16px]">
                    {showContentAbstract?.title || "--"}
                  </span>
                  <CloseOutlined
                    className="cursor-pointer"
                    onClick={() => {
                      setShowContentAbstract(null);
                    }}
                  />
                </div>
                <div className="text-[14px] text-[#2a2a2a] mt-3">内容要求</div>
                <div
                  className="mt-[8px] p-3 bg-[#fff] overflow-y-auto text-[#A0A0A0] h-[calc(100%-20px)]"
                  style={{
                    border: "1px solid #D9D9D9"
                  }}
                >
                  {showContentAbstract?.contentAbstract || ""}
                </div>
              </div>
            )}
          </div>
        </div>
      </OutlineExtractResLayout>

      <Modal
        destroyOnHidden
        open={openSelectMaterial}
        onCancel={closeSelectMaterial}
        title={"选择文件"}
        footer={
          <div className="flex gap-3 justify-end">
            <CommonBtn onClick={closeSelectMaterial}>取消</CommonBtn>
            <PrimaryBtn
              // disabled={!activeFile}
              onClick={handleMaterialExtract}
              loading={genOutlinesByMaterial.isLoading}
            >
              抽取大纲
            </PrimaryBtn>
          </div>
        }
        width={880}
        centered={true}
        styles={{
          body: {
            height: "430px",
            overflowY: "auto",
            boxSizing: "border-box",
            padding: "0 24px 20px"
          },
          content: {
            padding: "0"
          },
          header: {
            padding: "20px 24px"
          },
          footer: {
            padding: "20px 24px",
            borderTop: "solid 1px #EBEBEB"
          }
        }}
      >
        <SelectMaterialExtract
          handleSelectItem={handleSelectFile}
          materialTreeData={materialTreeData}
          activeFile={activeFile}
        />
      </Modal>
    </>
  );
};

export default UploadModelDoc;
