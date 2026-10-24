import { Drawer, Empty, message, Select, Spin } from "antd";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  filterOptions,
  handleSelectOpts,
  ResMap,
  ResOpt,
  SelectType
} from "./utils";
import TableHeader from "./TableHeader";
import TableItem, { ItemProps, ValueState } from "./TableItem";
import InfoDetail, { InfoConfirmTypes } from "./InfoDetail";
import { ExclamationCircleOutlined } from "@ant-design/icons";
import { useParams } from "react-router-dom";
import {
  queryAllSelectOptsApi,
  queryExtractResApi,
  updateIndicatorValueApi,
  addIndicatorValueApi
} from "./services";
import { DataExtractFileView } from "./DataExtractFileView";

const mockOpt = [
  {
    companyName: "天康生物管有限公司",
    tableName: "consolidated_balance", //资产负债表
    year: "2024",
    periodType: "年度"
  },
  {
    companyName: "芜湖三江高频焊管有限公司",
    tableName: "consolidated_income", //利润表
    year: "2024",
    periodType: "年度"
  }
];

const isMock = false;
const mockData = [
  {
    id: 2060,
    categoryId: 1056,
    parentId: 0,
    rootId: 2060,
    indicatorType: 1,
    indicatorName: "流动资产合计",
    dataType: 1,
    alias: ["流动资产"],
    sourceType: "合并资产负债表",
    state: 1,
    sortNo: 27000,
    creatorId: "admin",
    modifiedBy: "admin",
    status: 1,
    gmtCreate: "2025-07-03T03:39:16.000+00:00",
    gmtModified: "2025-07-08T21:47:02.000+00:00",
    subIndicators: [
      {
        id: 2061,
        categoryId: 1056,
        parentId: 2060,
        rootId: 2060,
        indicatorType: 1,
        indicatorName: "货币资金",
        parentIndicatorName: "流动资产合计",
        dataType: 1,
        description: "",
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 1000,
        creatorId: "admin",
        modifiedBy: "Xfanyue",
        status: 1,
        gmtCreate: "2025-07-03T03:39:28.000+00:00",
        gmtModified: "2025-07-11T06:35:27.000+00:00"
      },
      {
        id: 2062,
        categoryId: 1056,
        parentId: 2060,
        rootId: 2060,
        indicatorType: 1,
        indicatorName: "短期投资",
        parentIndicatorName: "流动资产合计",
        dataType: 1,
        description: "",
        alias: [""],
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 2000,
        creatorId: "admin",
        modifiedBy: "Xfanyue",
        status: 1,
        gmtCreate: "2025-07-03T03:39:40.000+00:00",
        gmtModified: "2025-07-10T07:14:09.000+00:00"
      },
      {
        id: 2063,
        categoryId: 1056,
        parentId: 2060,
        rootId: 2060,
        indicatorType: 1,
        indicatorName: "交易性金融资产",
        parentIndicatorName: "流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 3000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T03:39:47.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2064,
        categoryId: 1056,
        parentId: 2060,
        rootId: 2060,
        indicatorType: 1,
        indicatorName: "应收票据",
        parentIndicatorName: "流动资产合计",
        dataType: 1,
        description: "",
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 4000,
        creatorId: "admin",
        modifiedBy: "Xfanyue",
        status: 1,
        gmtCreate: "2025-07-03T03:40:26.000+00:00",
        gmtModified: "2025-07-10T05:47:58.000+00:00"
      },
      {
        id: 2065,
        categoryId: 1056,
        parentId: 2060,
        rootId: 2060,
        indicatorType: 1,
        indicatorName: "应收账款",
        parentIndicatorName: "流动资产合计",
        dataType: 1,
        description: "",
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 5000,
        creatorId: "admin",
        modifiedBy: "Xfanyue",
        status: 1,
        gmtCreate: "2025-07-03T03:40:31.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2066,
        categoryId: 1056,
        parentId: 2060,
        rootId: 2060,
        indicatorType: 1,
        indicatorName: "预付账款",
        parentIndicatorName: "流动资产合计",
        dataType: 1,
        description: "",
        alias: ["预付款项"],
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 6000,
        creatorId: "admin",
        modifiedBy: "Xfanyue",
        status: 1,
        gmtCreate: "2025-07-03T03:40:41.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2067,
        categoryId: 1056,
        parentId: 2060,
        rootId: 2060,
        indicatorType: 1,
        indicatorName: "应收利息",
        parentIndicatorName: "流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 7000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T03:40:41.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2068,
        categoryId: 1056,
        parentId: 2060,
        rootId: 2060,
        indicatorType: 1,
        indicatorName: "应收股利",
        parentIndicatorName: "流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 8000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T03:40:56.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2069,
        categoryId: 1056,
        parentId: 2060,
        rootId: 2060,
        indicatorType: 1,
        indicatorName: "其它应收款",
        parentIndicatorName: "流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 9000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T03:41:02.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2075,
        categoryId: 1056,
        parentId: 2060,
        rootId: 2060,
        indicatorType: 1,
        indicatorName: "存货",
        parentIndicatorName: "流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 10000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T03:42:33.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2076,
        categoryId: 1056,
        parentId: 2060,
        rootId: 2060,
        indicatorType: 1,
        indicatorName: "一年内到期的非流动资产",
        parentIndicatorName: "流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 11000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T03:43:44.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2077,
        categoryId: 1056,
        parentId: 2060,
        rootId: 2060,
        indicatorType: 1,
        indicatorName: "其他流动资产",
        parentIndicatorName: "流动资产合计",
        dataType: 1,
        sourceType: "合并利润表",
        state: 1,
        sortNo: 12000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T03:44:15.000+00:00",
        gmtModified: "2025-07-10T06:10:45.000+00:00",
        extractResult: {
          bop: {
            year: "2024",
            state: 3,
            errorMsg: "缺省值",
            source: [
              {
                tableName: "consolidated_income",
                id: 598,
                name: "其他流动资产",
                year: "2024",
                match: [
                  {
                    fileId: 117792,
                    sourceFileUrl:
                      "dev-rag-data/intelbrain-dw/1149/指标抽取测试/三江高频2024.12损益表.xls/V0/三江高频2024.12损益表.xls"
                  }
                ]
              }
            ]
          },
          eop: {
            year: "2024",
            state: 3,
            errorMsg: "缺省值",
            source: [
              {
                tableName: "consolidated_income",
                id: 599,
                name: "其他流动资产",
                year: "2024",
                match: [
                  {
                    fileId: 117792,
                    sourceFileUrl:
                      "dev-rag-data/intelbrain-dw/1149/指标抽取测试/三江高频2024.12损益表.xls/V0/三江高频2024.12损益表.xls"
                  }
                ]
              }
            ]
          }
        }
      },
      {
        id: 2293,
        categoryId: 1056,
        parentId: 2060,
        rootId: 2060,
        indicatorType: 1,
        indicatorName: "结算备付金",
        parentIndicatorName: "流动资产合计",
        dataType: 1,
        description: "金融企业专用",
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 13000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T06:35:17.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2294,
        categoryId: 1056,
        parentId: 2060,
        rootId: 2060,
        indicatorType: 1,
        indicatorName: "拆成资金",
        parentIndicatorName: "流动资产合计",
        dataType: 1,
        description: "金融企业专用",
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 14000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T06:36:37.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2295,
        categoryId: 1056,
        parentId: 2060,
        rootId: 2060,
        indicatorType: 1,
        indicatorName: "以公允价值计量且其变动计入当期损益的金融资产",
        parentIndicatorName: "流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 15000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T06:37:07.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2296,
        categoryId: 1056,
        parentId: 2060,
        rootId: 2060,
        indicatorType: 1,
        indicatorName: "衍生金融资产",
        parentIndicatorName: "流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 16000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T06:37:38.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2297,
        categoryId: 1056,
        parentId: 2060,
        rootId: 2060,
        indicatorType: 1,
        indicatorName: "应收款项融资",
        parentIndicatorName: "流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 17000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T06:38:06.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2298,
        categoryId: 1056,
        parentId: 2060,
        rootId: 2060,
        indicatorType: 1,
        indicatorName: "应收保费",
        parentIndicatorName: "流动资产合计",
        dataType: 1,
        description: "金融企业专用",
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 18000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T06:47:35.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2299,
        categoryId: 1056,
        parentId: 2060,
        rootId: 2060,
        indicatorType: 1,
        indicatorName: "应收分保账款",
        parentIndicatorName: "流动资产合计",
        dataType: 1,
        description: "金融企业专用",
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 19000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T06:47:56.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2300,
        categoryId: 1056,
        parentId: 2060,
        rootId: 2060,
        indicatorType: 1,
        indicatorName: "应收分保合同准备金",
        parentIndicatorName: "流动资产合计",
        dataType: 1,
        description: "金融企业专用",
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 20000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T06:50:24.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2301,
        categoryId: 1056,
        parentId: 2060,
        rootId: 2060,
        indicatorType: 1,
        indicatorName: "买入返售金融资产",
        parentIndicatorName: "流动资产合计",
        dataType: 1,
        description: "金融企业专用",
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 21000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T06:51:00.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2302,
        categoryId: 1056,
        parentId: 2060,
        rootId: 2060,
        indicatorType: 1,
        indicatorName: "合同资产",
        parentIndicatorName: "流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 22000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T06:51:34.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2303,
        categoryId: 1056,
        parentId: 2060,
        rootId: 2060,
        indicatorType: 1,
        indicatorName: "持有待售资产",
        parentIndicatorName: "流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 23000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T06:51:49.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      }
    ]
  },
  {
    id: 2079,
    categoryId: 1056,
    parentId: 0,
    rootId: 2079,
    indicatorType: 1,
    indicatorName: "非流动资产合计",
    dataType: 1,
    alias: ["非流动资产"],
    sourceType: "合并资产负债表",
    state: 1,
    sortNo: 29000,
    creatorId: "admin",
    modifiedBy: "admin",
    status: 1,
    gmtCreate: "2025-07-03T05:39:48.000+00:00",
    gmtModified: "2025-07-08T21:47:02.000+00:00",
    subIndicators: [
      {
        id: 2080,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "可供出售金融资产",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 1000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:40:15.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2082,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "持有至到期投资",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 2000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:41:19.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2083,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "长期应收款",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 3000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:41:26.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2084,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "长期股权投资",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 4000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:41:42.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2085,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "长期合债权反投资",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 5000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:42:16.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2086,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "投资性房地产",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 6000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:42:27.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2087,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "固定资产原价",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        alias: ["固定资产原值"],
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 7000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:42:36.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2089,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "累计折旧",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 8000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:45:56.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2090,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "生产性生物资产",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 9000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:45:58.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2091,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "固定资产清理",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 8500,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:46:00.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2092,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "在建工程",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 8250,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:46:02.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2093,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "其他非流动资产",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 10000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:47:04.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2094,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "开发支出",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 9500,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:47:06.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2095,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "无形资产",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 9250,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:47:08.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2096,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "油气资产",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 9125,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:47:10.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2097,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "商誉",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 9750,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:49:55.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2098,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "递延所得税资产",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 9875,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:49:57.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2099,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "长期待摊费用",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 9812.5,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:49:58.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2304,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "发放贷款及垫款",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        description: "金融企业专用",
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 11000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T06:52:28.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2305,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "债券投资",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        description: "金融企业专用",
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 12000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T07:11:52.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2306,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "其他债券投资",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        description: "金融企业专用",
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 13000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T07:12:18.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2307,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "其他权益工具投资",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 14000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T07:13:13.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2308,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "其他非流动金融资产",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 15000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T07:20:28.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2309,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "固定资产",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 16000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T07:21:08.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2310,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "固定资产减值准备",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 17000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T07:22:43.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2311,
        categoryId: 1056,
        parentId: 2079,
        rootId: 2079,
        indicatorType: 1,
        indicatorName: "使用权资产",
        parentIndicatorName: "非流动资产合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 18000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T07:23:43.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      }
    ]
  },
  {
    id: 2100,
    categoryId: 1056,
    parentId: 0,
    rootId: 2100,
    indicatorType: 1,
    indicatorName: "流动负债合计",
    dataType: 1,
    alias: ["流动负债"],
    sourceType: "合并资产负债表",
    state: 1,
    sortNo: 30000,
    creatorId: "admin",
    modifiedBy: "admin",
    status: 1,
    gmtCreate: "2025-07-03T05:51:51.000+00:00",
    gmtModified: "2025-07-08T21:47:02.000+00:00",
    subIndicators: [
      {
        id: 2101,
        categoryId: 1056,
        parentId: 2100,
        rootId: 2100,
        indicatorType: 1,
        indicatorName: "短期借款",
        parentIndicatorName: "流动负债合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 1000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:52:11.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2103,
        categoryId: 1056,
        parentId: 2100,
        rootId: 2100,
        indicatorType: 1,
        indicatorName: "交易性金融负债",
        parentIndicatorName: "流动负债合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 1500,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:52:15.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2104,
        categoryId: 1056,
        parentId: 2100,
        rootId: 2100,
        indicatorType: 1,
        indicatorName: "其他应付款",
        parentIndicatorName: "流动负债合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 2500,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:52:23.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2105,
        categoryId: 1056,
        parentId: 2100,
        rootId: 2100,
        indicatorType: 1,
        indicatorName: "应付股利",
        parentIndicatorName: "流动负债合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 2000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:52:24.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2106,
        categoryId: 1056,
        parentId: 2100,
        rootId: 2100,
        indicatorType: 1,
        indicatorName: "应付利润",
        parentIndicatorName: "流动负债合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 1750,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:52:26.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2107,
        categoryId: 1056,
        parentId: 2100,
        rootId: 2100,
        indicatorType: 1,
        indicatorName: "应付利息",
        parentIndicatorName: "流动负债合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 1625,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:52:26.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2108,
        categoryId: 1056,
        parentId: 2100,
        rootId: 2100,
        indicatorType: 1,
        indicatorName: "应交税费",
        parentIndicatorName: "流动负债合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 1562.5,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:52:28.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2109,
        categoryId: 1056,
        parentId: 2100,
        rootId: 2100,
        indicatorType: 1,
        indicatorName: "应付职工薪酬",
        parentIndicatorName: "流动负债合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 1531.25,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:52:29.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2110,
        categoryId: 1056,
        parentId: 2100,
        rootId: 2100,
        indicatorType: 1,
        indicatorName: "预收账款",
        parentIndicatorName: "流动负债合计",
        dataType: 1,
        alias: ["预收款项"],
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 1515.625,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:52:29.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2111,
        categoryId: 1056,
        parentId: 2100,
        rootId: 2100,
        indicatorType: 1,
        indicatorName: "应付账款",
        parentIndicatorName: "流动负债合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 1507.8125,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:52:29.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2112,
        categoryId: 1056,
        parentId: 2100,
        rootId: 2100,
        indicatorType: 1,
        indicatorName: "应付票据",
        parentIndicatorName: "流动负债合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 1503.90625,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:52:29.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2113,
        categoryId: 1056,
        parentId: 2100,
        rootId: 2100,
        indicatorType: 1,
        indicatorName: "一年内到期的非流动负债",
        parentIndicatorName: "流动负债合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 3500,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:53:57.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2116,
        categoryId: 1056,
        parentId: 2100,
        rootId: 2100,
        indicatorType: 1,
        indicatorName: "其他流动负债",
        parentIndicatorName: "流动负债合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 3750,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:54:04.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2313,
        categoryId: 1056,
        parentId: 2100,
        rootId: 2100,
        indicatorType: 1,
        indicatorName: "向中央银行借款",
        parentIndicatorName: "流动负债合计",
        dataType: 1,
        description: "金融企业专用",
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 4750,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T07:28:14.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2314,
        categoryId: 1056,
        parentId: 2100,
        rootId: 2100,
        indicatorType: 1,
        indicatorName: "拆入资金",
        parentIndicatorName: "流动负债合计",
        dataType: 1,
        description: "金融企业专用",
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 5750,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T07:28:59.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2315,
        categoryId: 1056,
        parentId: 2100,
        rootId: 2100,
        indicatorType: 1,
        indicatorName: "衍生金融负债",
        parentIndicatorName: "流动负债合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 6750,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T07:29:21.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2316,
        categoryId: 1056,
        parentId: 2100,
        rootId: 2100,
        indicatorType: 1,
        indicatorName: "合同负债",
        parentIndicatorName: "流动负债合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 7750,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T07:30:13.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2317,
        categoryId: 1056,
        parentId: 2100,
        rootId: 2100,
        indicatorType: 1,
        indicatorName: "卖出回购金融资产款",
        parentIndicatorName: "流动负债合计",
        dataType: 1,
        description: "金融企业专用",
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 8750,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T07:30:36.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2318,
        categoryId: 1056,
        parentId: 2100,
        rootId: 2100,
        indicatorType: 1,
        indicatorName: "吸收存款及同业存放",
        parentIndicatorName: "流动负债合计",
        dataType: 1,
        description: "金融企业专用",
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 9750,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T07:31:11.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2319,
        categoryId: 1056,
        parentId: 2100,
        rootId: 2100,
        indicatorType: 1,
        indicatorName: "代理买卖证券款",
        parentIndicatorName: "流动负债合计",
        dataType: 1,
        description: "金融企业专用",
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 10750,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T07:31:22.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2320,
        categoryId: 1056,
        parentId: 2100,
        rootId: 2100,
        indicatorType: 1,
        indicatorName: "代理承销证券款",
        parentIndicatorName: "流动负债合计",
        dataType: 1,
        description: "金融企业专用",
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 11750,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T07:31:35.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2321,
        categoryId: 1056,
        parentId: 2100,
        rootId: 2100,
        indicatorType: 1,
        indicatorName: "应付手续费及佣金",
        parentIndicatorName: "流动负债合计",
        dataType: 1,
        description: "金融企业专用",
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 12750,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T07:32:26.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2322,
        categoryId: 1056,
        parentId: 2100,
        rootId: 2100,
        indicatorType: 1,
        indicatorName: "应付分保账款",
        parentIndicatorName: "流动负债合计",
        dataType: 1,
        description: "金融企业专用",
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 13750,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T07:32:37.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2323,
        categoryId: 1056,
        parentId: 2100,
        rootId: 2100,
        indicatorType: 1,
        indicatorName: "持有待售负债",
        parentIndicatorName: "流动负债合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 14750,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T07:33:10.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      }
    ]
  },
  {
    id: 2117,
    categoryId: 1056,
    parentId: 0,
    rootId: 2117,
    indicatorType: 1,
    indicatorName: "非流动负债合计",
    dataType: 1,
    description: "",
    alias: ["非流动负债"],
    sourceType: "合并资产负债表",
    state: 1,
    sortNo: 31000,
    creatorId: "admin",
    modifiedBy: "admin",
    status: 1,
    gmtCreate: "2025-07-03T05:56:11.000+00:00",
    gmtModified: "2025-07-08T21:47:02.000+00:00",
    subIndicators: [
      {
        id: 2119,
        categoryId: 1056,
        parentId: 2117,
        rootId: 2117,
        indicatorType: 1,
        indicatorName: "长期借款",
        parentIndicatorName: "非流动负债合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 1000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:56:32.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2120,
        categoryId: 1056,
        parentId: 2117,
        rootId: 2117,
        indicatorType: 1,
        indicatorName: "其他非流动负债",
        parentIndicatorName: "非流动负债合计",
        dataType: 1,
        description: "",
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 2000,
        creatorId: "admin",
        modifiedBy: "Xfanyue",
        status: 1,
        gmtCreate: "2025-07-03T05:56:36.000+00:00",
        gmtModified: "2025-07-10T10:00:13.000+00:00"
      },
      {
        id: 2121,
        categoryId: 1056,
        parentId: 2117,
        rootId: 2117,
        indicatorType: 1,
        indicatorName: "递延所得税负债",
        parentIndicatorName: "非流动负债合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 1500,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:56:36.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2122,
        categoryId: 1056,
        parentId: 2117,
        rootId: 2117,
        indicatorType: 1,
        indicatorName: "递延收益",
        parentIndicatorName: "非流动负债合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 1250,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:56:37.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2123,
        categoryId: 1056,
        parentId: 2117,
        rootId: 2117,
        indicatorType: 1,
        indicatorName: "预计负债",
        parentIndicatorName: "非流动负债合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 1125,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:56:37.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2124,
        categoryId: 1056,
        parentId: 2117,
        rootId: 2117,
        indicatorType: 1,
        indicatorName: "专项应付款",
        parentIndicatorName: "非流动负债合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 1062.5,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:56:37.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2125,
        categoryId: 1056,
        parentId: 2117,
        rootId: 2117,
        indicatorType: 1,
        indicatorName: "长期应付款",
        parentIndicatorName: "非流动负债合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 1031.25,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:56:38.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2126,
        categoryId: 1056,
        parentId: 2117,
        rootId: 2117,
        indicatorType: 1,
        indicatorName: "应付债券",
        parentIndicatorName: "非流动负债合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 1015.625,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:56:38.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00",
        subIndicators: [
          {
            id: 2325,
            categoryId: 1056,
            parentId: 2126,
            rootId: 2117,
            indicatorType: 1,
            indicatorName: "应付债券-优先股",
            parentIndicatorName: "应付债券",
            dataType: 1,
            sourceType: "合并资产负债表",
            state: 1,
            sortNo: 1000,
            creatorId: "admin",
            modifiedBy: "wangxuecheng",
            status: 1,
            gmtCreate: "2025-07-04T07:34:51.000+00:00",
            gmtModified: "2025-07-11T05:44:17.000+00:00"
          },
          {
            id: 2326,
            categoryId: 1056,
            parentId: 2126,
            rootId: 2117,
            indicatorType: 1,
            indicatorName: "应付债券-永续债",
            parentIndicatorName: "应付债券",
            dataType: 1,
            sourceType: "合并资产负债表",
            state: 1,
            sortNo: 2000,
            creatorId: "admin",
            modifiedBy: "wangxuecheng",
            status: 1,
            gmtCreate: "2025-07-04T07:35:04.000+00:00",
            gmtModified: "2025-07-11T05:53:00.000+00:00"
          }
        ]
      },
      {
        id: 2324,
        categoryId: 1056,
        parentId: 2117,
        rootId: 2117,
        indicatorType: 1,
        indicatorName: "保险合同准备金",
        parentIndicatorName: "非流动负债合计",
        dataType: 1,
        description: "金融企业专用",
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 3000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T07:34:03.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2327,
        categoryId: 1056,
        parentId: 2117,
        rootId: 2117,
        indicatorType: 1,
        indicatorName: "租赁负债",
        parentIndicatorName: "非流动负债合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 4000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T07:35:24.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      }
    ]
  },
  {
    id: 2127,
    categoryId: 1056,
    parentId: 0,
    rootId: 2127,
    indicatorType: 1,
    indicatorName: "所有者权益合计",
    dataType: 1,
    description: "",
    alias: ["股东权益合计", "所有者权益(或股东权益)合计"],
    sourceType: "合并资产负债表",
    state: 1,
    sortNo: 32000,
    creatorId: "admin",
    modifiedBy: "admin",
    status: 1,
    gmtCreate: "2025-07-03T05:58:13.000+00:00",
    gmtModified: "2025-07-08T22:15:50.000+00:00",
    subIndicators: [
      {
        id: 2128,
        categoryId: 1056,
        parentId: 2127,
        rootId: 2127,
        indicatorType: 1,
        indicatorName: "实收资本（或股本）",
        parentIndicatorName: "所有者权益合计",
        dataType: 1,
        alias: ["实收资本、股本"],
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 1000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:58:21.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2131,
        categoryId: 1056,
        parentId: 2127,
        rootId: 2127,
        indicatorType: 1,
        indicatorName: "外币报表折算差额",
        parentIndicatorName: "所有者权益合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 2000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:58:37.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2132,
        categoryId: 1056,
        parentId: 2127,
        rootId: 2127,
        indicatorType: 1,
        indicatorName: "未分配利润",
        parentIndicatorName: "所有者权益合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 1500,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:58:39.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2133,
        categoryId: 1056,
        parentId: 2127,
        rootId: 2127,
        indicatorType: 1,
        indicatorName: "盈余公积",
        parentIndicatorName: "所有者权益合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 1250,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:58:40.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2134,
        categoryId: 1056,
        parentId: 2127,
        rootId: 2127,
        indicatorType: 1,
        indicatorName: "库存股",
        parentIndicatorName: "所有者权益合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 1125,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:58:42.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2135,
        categoryId: 1056,
        parentId: 2127,
        rootId: 2127,
        indicatorType: 1,
        indicatorName: "资本公积",
        parentIndicatorName: "所有者权益合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 1062.5,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:58:43.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2136,
        categoryId: 1056,
        parentId: 2127,
        rootId: 2127,
        indicatorType: 1,
        indicatorName: "少数股东权益",
        parentIndicatorName: "所有者权益合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 3000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-03T05:59:28.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2329,
        categoryId: 1056,
        parentId: 2127,
        rootId: 2127,
        indicatorType: 1,
        indicatorName: "其他权益工具",
        parentIndicatorName: "所有者权益合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 4000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T08:26:44.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00",
        subIndicators: [
          {
            id: 2332,
            categoryId: 1056,
            parentId: 2329,
            rootId: 2127,
            indicatorType: 1,
            indicatorName: "其他权益工具-优先股",
            parentIndicatorName: "其他权益工具",
            dataType: 1,
            sourceType: "合并资产负债表",
            state: 1,
            sortNo: 1000,
            creatorId: "admin",
            modifiedBy: "wangxuecheng",
            status: 1,
            gmtCreate: "2025-07-04T08:28:15.000+00:00",
            gmtModified: "2025-07-11T05:46:05.000+00:00"
          },
          {
            id: 2333,
            categoryId: 1056,
            parentId: 2329,
            rootId: 2127,
            indicatorType: 1,
            indicatorName: "其他权益工具-永续债",
            parentIndicatorName: "其他权益工具",
            dataType: 1,
            sourceType: "合并资产负债表",
            state: 1,
            sortNo: 2000,
            creatorId: "admin",
            modifiedBy: "wangxuecheng",
            status: 1,
            gmtCreate: "2025-07-04T08:28:33.000+00:00",
            gmtModified: "2025-07-11T05:53:11.000+00:00"
          }
        ]
      },
      {
        id: 2334,
        categoryId: 1056,
        parentId: 2127,
        rootId: 2127,
        indicatorType: 1,
        indicatorName: "其他综合收益",
        parentIndicatorName: "所有者权益合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 5000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T08:29:00.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2335,
        categoryId: 1056,
        parentId: 2127,
        rootId: 2127,
        indicatorType: 1,
        indicatorName: "专项储备",
        parentIndicatorName: "所有者权益合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 6000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T08:29:18.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2336,
        categoryId: 1056,
        parentId: 2127,
        rootId: 2127,
        indicatorType: 1,
        indicatorName: "一般风险准备",
        parentIndicatorName: "所有者权益合计",
        dataType: 1,
        description: "金融企业专用",
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 7000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T08:29:35.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      },
      {
        id: 2338,
        categoryId: 1056,
        parentId: 2127,
        rootId: 2127,
        indicatorType: 1,
        indicatorName: "归属于母公司股东权益合计",
        parentIndicatorName: "所有者权益合计",
        dataType: 1,
        sourceType: "合并资产负债表",
        state: 1,
        sortNo: 8000,
        creatorId: "admin",
        modifiedBy: "admin",
        status: 1,
        gmtCreate: "2025-07-04T08:31:27.000+00:00",
        gmtModified: "2025-07-08T21:47:02.000+00:00"
      }
    ]
  },
  {
    id: 2312,
    categoryId: 1056,
    parentId: 0,
    rootId: 2312,
    indicatorType: 1,
    indicatorName: "资产总计",
    dataType: 1,
    sourceType: "合并资产负债表",
    state: 1,
    sortNo: 47125,
    creatorId: "admin",
    modifiedBy: "admin",
    status: 1,
    gmtCreate: "2025-07-04T07:24:31.000+00:00",
    gmtModified: "2025-07-08T21:47:02.000+00:00"
  },
  {
    id: 2328,
    categoryId: 1056,
    parentId: 0,
    rootId: 2328,
    indicatorType: 1,
    indicatorName: "负债合计",
    dataType: 1,
    sourceType: "合并资产负债表",
    state: 1,
    sortNo: 48125,
    creatorId: "admin",
    modifiedBy: "admin",
    status: 1,
    gmtCreate: "2025-07-04T07:36:08.000+00:00",
    gmtModified: "2025-07-08T21:47:02.000+00:00"
  },
  {
    id: 2337,
    categoryId: 1056,
    parentId: 0,
    rootId: 2337,
    indicatorType: 1,
    indicatorName: "负债和所有者权益总计",
    dataType: 1,
    alias: ["负债和股东权益总计"],
    sourceType: "合并资产负债表",
    state: 1,
    sortNo: 49125,
    creatorId: "admin",
    modifiedBy: "admin",
    status: 1,
    gmtCreate: "2025-07-04T08:30:26.000+00:00",
    gmtModified: "2025-07-08T21:47:02.000+00:00"
  }
];

const tableNameMapping: any[] = [
  {
    key: "合并资产负债表",
    value: "consolidated_balance"
  },
  {
    key: "合并现金流量表",
    value: "consolidated_cash_flow"
  },
  {
    key: "合并利润表",
    value: "consolidated_income"
  }
];

const initOpts = {
  tables: [],
  companys: [],
  timeRange: []
};

export const getIcon = (type: ValueState) => {
  let color = "#34C759";
  switch (type) {
    case ValueState.HighReliability:
      color = "#34C759";
      break;
    case ValueState.NoSource:
      color = "#FF9500";
      break;
    case ValueState.Multivalued:
    case ValueState.VerificationFailed:
      color = "#FF3B30";
      break;
    default:
      break;
  }
  return (
    <ExclamationCircleOutlined
      rotate={180}
      style={{
        fontSize: "16px",
        color
      }}
    />
  );
};

interface IDataExtract {
  knowledgeBaseName: string;
}

const DataExtract = (props: IDataExtract) => {
  const { id, fileId } = useParams();
  const totalOptsRef = useRef<ResMap>(initOpts);
  // 选表
  const [tablesSelectionOpts, setTablesSelectionOpts] = useState<ResOpt[]>([]);
  const [tablesSelectionValue, setTablesSelectionValue] = useState("");
  // 选公司
  const [companysSelectionOpts, setCompanysSelectionOpts] = useState<ResOpt[]>(
    []
  );
  const [companysSelectionValue, setCompanysSelectionValue] = useState("");
  // 选时间范围
  const [timeRangeSelectionOpts, setTimeRangeSelectionOpts] = useState<
    ResOpt[]
  >([]);
  const [timeRangeSelectionValue, setTimeRangeSelectionValue] = useState("");

  const updateIndicatorValue = updateIndicatorValueApi();
  const addIndicatorValue = addIndicatorValueApi();
  const queryAllSelectOpts = queryAllSelectOptsApi({ id, fileId });
  const queryExtractRes = queryExtractResApi({
    id,
    fileId,
    companyName: companysSelectionValue,
    tableName: tablesSelectionValue,
    year: timeRangeSelectionValue.split("@")[0],
    periodType: timeRangeSelectionValue.split("@")[1]
  });

  // 默认选择，需要更新时默认选择第一项
  const defaultSelect = (type: SelectType, newOpts: ResOpt[]) => {
    const curOpt = newOpts[0];
    if (!curOpt) return;
    switch (type) {
      case "tables":
        setTablesSelectionOpts(newOpts);
        setTablesSelectionValue(curOpt.value || "");
        break;
      case "companys":
        setCompanysSelectionOpts(newOpts);
        setCompanysSelectionValue(curOpt.value || "");
        break;
      case "timeRange":
        setTimeRangeSelectionOpts(newOpts);
        setTimeRangeSelectionValue(curOpt.value || "");
        break;
      default:
        break;
    }
  };

  // 改变表格时，联级改变公司和时间范围
  const handleTableChange = (value: string) => {
    setInfoDetail("");
    defaultSelect("tables", totalOptsRef.current.tables);
    setTablesSelectionValue(value);
    const curCompanysOpts = filterOptions(
      { table: value },
      totalOptsRef.current.companys
    );
    defaultSelect("companys", curCompanysOpts);
    if (curCompanysOpts[0]) {
      const curTimeRangeOpts = filterOptions(
        { table: value, company: curCompanysOpts[0].value },
        totalOptsRef.current.timeRange
      );
      defaultSelect("timeRange", curTimeRangeOpts);
    } else {
      setTimeRangeSelectionValue("");
      setTimeRangeSelectionOpts([]);
    }
  };

  // 改变公司时，联级改变时间范围
  const handleCompanyChange = (value: string) => {
    setInfoDetail("");
    setCompanysSelectionValue(value);
    const curTimeRangeOpts = filterOptions(
      { table: tablesSelectionValue, company: value },
      totalOptsRef.current.timeRange
    );
    defaultSelect("timeRange", curTimeRangeOpts);
  };

  // 改变时间范围
  const handleTimeRangeChange = (value: string) => {
    setInfoDetail("");
    setTimeRangeSelectionValue(value);
  };

  useEffect(() => {
    const realOpts = queryAllSelectOpts.data;
    if (!realOpts || !realOpts.length) return;
    const res = handleSelectOpts(realOpts);
    totalOptsRef.current = res;
    if (res.tables.length) {
      handleTableChange(res.tables[0].value);
    }
  }, [queryAllSelectOpts?.data]);

  // 当前点击的item
  const [infoDetail, setInfoDetail] = useState<any>();

  const clickItem = (item: any) => {
    setInfoDetail(item);
  };

  // 全部展开收起
  const [isAllExpand, setIsAllExpand] = useState<boolean>(true);

  const renderTable = (tree: ItemProps[], depth = 0) => {
    const treeLen = tree && tree.length ? tree.length : 0;
    if (!tree || treeLen === 0) {
      return null;
    }
    return tree.map((node: ItemProps, idx: number) => {
      if (!node.subIndicators || node.subIndicators.length === 0) {
        return (
          <TableItem
            clickItem={clickItem}
            key={node.id}
            item={node}
            depth={depth}
            isExpanded={isAllExpand}
            handleUpdateIndicatorValue={handleUpdateIndicatorValue}
            handleAddIndicatorValue={handleAddIndicatorValue}
          />
        );
      } else {
        return (
          <TableItem
            clickItem={clickItem}
            key={node.id}
            item={node}
            depth={depth}
            isExpanded={isAllExpand}
            handleUpdateIndicatorValue={handleUpdateIndicatorValue}
            handleAddIndicatorValue={handleAddIndicatorValue}
          >
            {renderTable(node.subIndicators, depth + 1)}
          </TableItem>
        );
      }
    });
  };

  const checkTreeState = (node: any) => {
    if (node.subIndicators && node.subIndicators.length > 0) {
      for (const child of node.subIndicators) {
        const result = checkTreeState(child);
        if (result) {
          return true;
        }
      }
    }

    if (node.extractResult) {
      const { bop, eop } = node.extractResult;
      const validStates = [
        ValueState.Multivalued,
        ValueState.VerificationFailed
      ];

      if (
        (bop && validStates.includes(bop.state)) ||
        (eop && validStates.includes(eop.state))
      ) {
        return true;
      }
    }

    return false;
  };
  const treeData = useMemo(() => {
    const realTree = queryExtractRes.data;
    return isMock ? mockData : realTree || [];
  }, [queryExtractRes.data]);

  const isExitError = useMemo(() => {
    return treeData.some((node: any) => checkTreeState(node));
  }, [treeData]);

  const [fileViewInfo, setFileViewInfo] = useState<any>("");
  const handleCloseFileView = () => {
    setFileViewInfo("");
  };

  const handleUpdateIndicatorValue = async (params: any) => {
    await updateIndicatorValue.mutateAsync({
      kbId: id,
      params
    });
    queryExtractRes.refetch();
  };

  const handleFileView = (data: any) => {
    setFileViewInfo(data);
  };

  const handleAddIndicatorValue = async (params: any) => {
    const _paramInfo = { ...paramInfo } as any;
    console.log(paramInfo);
    const index = tableNameMapping.findIndex(
      (i: any) => i.key === _paramInfo.tableName
    );
    const comIndex = companysSelectionOpts.findIndex(
      (i: any) => i.value === companysSelectionValue
    );
    const [year, periodType] = timeRangeSelectionValue.split("@");
    const _params = {
      ...params,
      companyName:
        comIndex >= 0 ? companysSelectionOpts[comIndex].companyName : "",
      companyFullName:
        comIndex >= 0 ? companysSelectionOpts[comIndex].companyFullName : "",
      year,
      periodType,
      tableName: index >= 0 ? tableNameMapping[index].value : "",
      knowledgeBaseName: props.knowledgeBaseName
    };

    await addIndicatorValue.mutateAsync({
      kbId: id,
      params: {
        ..._params
      }
    });
    queryExtractRes.refetch();
  };

  const [infoDetailLoading, setInfoDetailLoading] = useState<boolean>(false);
  const handleMultiValue = async ({ row, data }: any) => {
    try {
      setInfoDetailLoading(true);
      let params: any = {
        refTableNames: [],
        refIds: []
      };
      (row?.source || []).forEach((item: any) => {
        params.refTableNames.push(item.tableName);
        params.refIds.push(item.id);
      });
      params = {
        ...params,
        ...data
      };
      await handleUpdateIndicatorValue(params);
      setInfoDetailLoading(false);
    } catch (e) {
      console.log(e);
      setInfoDetailLoading(false);
    }
  };
  // 右侧回调事件
  const confirmInfoByType = (type: InfoConfirmTypes, row: any, data: any) => {
    console.log(type, row, data);

    switch (type) {
      case InfoConfirmTypes.CLOSE:
        setInfoDetail("");
        break;
      case InfoConfirmTypes.MULTI_VALUED_CONFLICT:
        handleMultiValue({ row, data });
        break;
      case InfoConfirmTypes.SHOW_SOURCE_FILE:
        if (!data || !data?.fileInfo) {
          message.warning("找不到溯源文件");
          return;
        }
        handleFileView(data.fileInfo);
        break;
      default:
        break;
    }
  };

  const paramInfo = useMemo(() => {
    const obj = tablesSelectionOpts.find(
      (i) => String(i.categoryId) === tablesSelectionValue
    );

    return obj || {};
  }, [tablesSelectionOpts, tablesSelectionValue]);

  return (
    <>
      <div className="w-full h-full box-border flex">
        <>
          <div
            style={{
              width: infoDetail ? "calc(100% - 410px)" : "100%",
              marginRight: infoDetail ? "30px" : 0
            }}
          >
            <div className="flex justify-between mt-[7px]">
              <div className="flex gap-3">
                {/* {JSON.stringify(paramInfo)} */}
                <Select
                  options={tablesSelectionOpts}
                  className="h-[32px] w-[169px] cec-select"
                  value={tablesSelectionValue}
                  disabled={!tablesSelectionOpts.length}
                  onSelect={(value) => {
                    handleTableChange(value);
                  }}
                />
                <Select
                  options={companysSelectionOpts}
                  className="h-[32px] w-[169px] cec-select"
                  value={companysSelectionValue}
                  disabled={!companysSelectionOpts.length}
                  onSelect={(value) => {
                    handleCompanyChange(value);
                  }}
                />
                <Select
                  options={timeRangeSelectionOpts}
                  className="h-[32px] w-[169px] cec-select"
                  value={timeRangeSelectionValue}
                  disabled={!timeRangeSelectionOpts.length}
                  onSelect={(value) => {
                    handleTimeRangeChange(value);
                  }}
                />
              </div>
              <div className="flex gap-[16px] mr-[30px] h-[32px] items-center">
                {/* <div className="text-[#888888]">
                  <span className="mr-[4px] leading-[32px]">
                    {getIcon(ValueState.HighReliability)}
                  </span>
                  可靠度高
                </div>
                <div className="text-[#888888]">
                  <span className="mr-[4px] leading-[32px]">
                    {getIcon(ValueState.NoSource)}
                  </span>
                  无溯源
                </div> */}
                {isExitError ? (
                  <div className="text-[#888888]">
                    <span className="mr-[4px] leading-[32px]">
                      {getIcon(ValueState.VerificationFailed)}
                    </span>
                    有问题
                  </div>
                ) : null}
              </div>
            </div>
            {queryExtractRes.isFetching ? (
              <div className="w-full h-full flex justify-center items-center">
                <Spin size="large" />
              </div>
            ) : (
              <>
                {treeData && treeData.length ? (
                  <div className="mt-3 h-[calc(100%-51px)] box-border overflow-y-auto w-full">
                    <TableHeader />
                    {renderTable(treeData)}
                  </div>
                ) : (
                  <div className="w-full h-full flex justify-center items-center">
                    <Empty />
                  </div>
                )}
              </>
            )}
          </div>
          <div
            className="box-border overflow-hidden"
            style={{
              width: infoDetail ? "410px" : 0,
              borderLeft: infoDetail ? "1px solid #ECECEE" : "none"
            }}
          >
            <InfoDetail
              item={infoDetail}
              confirmInfoByType={confirmInfoByType}
              isLoading={infoDetailLoading}
            />
          </div>
        </>
      </div>
      <Drawer
        destroyOnClose
        width={900}
        open={fileViewInfo}
        onClose={handleCloseFileView}
        styles={{
          header: {
            display: "none"
          },
          footer: {
            display: "none"
          },
          body: {
            padding: 0
          }
        }}
      >
        <DataExtractFileView
          fileViewInfo={fileViewInfo}
          onClose={handleCloseFileView}
        />
      </Drawer>
    </>
  );
};

export default DataExtract;
